"""Gate D: isolated single-purpose ASGI ingress, offline only."""
import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient
import pytest

from app.media07_studio_gateway_v1291 import app
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS


@pytest.fixture
def configured(monkeypatch):
    for name in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS):
        monkeypatch.setenv(name, "0")
    env = {
        "SCEC_ENV": "staging",
        "SCEC_IDENTITY_MODE": "bound",
        "SCEC_MEDIA07_STAGING_ENABLED": "1",
        "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED": "1",
        "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED": "1",
        "SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY": "unique-gated-hmac-synthetic-bridge-key-1234567",
        "SCEC_IDENTITY_SIGNING_KEY": "distinct-identity-key-for-synthetic-test-123",
        "SCEC_ALLOWED_ORGANIZATION_IDS": "00000000-0000-4000-8000-000000000001",
        "SCEC_MEDIA07_DRAFT_ORGANIZATION_ID": "00000000-0000-4000-8000-000000000001",
        "SCEC_MEDIA07_EMPTY_LIST_ID": "3",
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    import app.media07_studio_bridge_v1290 as bridge
    calls = []
    def fake_create(req, tenant):
        calls.append((req, str(tenant)))
        return {"release": "MEDIA-07.3",
                "organization_id": str(tenant), "campaign_id": 42,
                "campaign_status": "draft", "draft_reused": len(calls) > 1,
                "fingerprint": "b" * 64, "synthetic_only": True, "sent": False}
    monkeypatch.setattr(bridge, "create_draft", fake_create)
    return env, calls


def synthetic_request(env):
    html = "<html><body><h1>[SYNTHETIC] Staging fixture</h1></body></html>"
    payload = {
        "schema_version": "scec.media07.listmonk-draft/1",
        "organization_id": "00000000-0000-4000-8000-000000000001",
        "newsletter_ref": "wp-newsletter:55",
        "studio_revision_sha256": "a" * 64,
        "rendered_html_sha256": hashlib.sha256(html.encode()).hexdigest(),
        "title": "[SYNTHETIC] Research",
        "subject": "[SYNTHETIC] Research",
        "preheader": "Not for delivery",
        "body_html": html,
        "altbody": "Synthetic research test",
        "synthetic_only": True,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode()
    stamp = str(int(time.time()))
    digest = hmac.new(env["SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY"].encode(),
                      stamp.encode() + b"\n" + raw, hashlib.sha256).hexdigest()
    return raw, {
        "Content-Type": "application/json",
        "X-SCEC-MEDIA07-Timestamp": stamp,
        "X-SCEC-MEDIA07-Signature": digest,
    }


def test_gateway_exposes_only_signed_draft_ingress(configured):
    env, calls = configured
    with TestClient(app) as client:
        for path in (
            "/", "/docs", "/openapi.json", "/health", "/v1/newsletter-studio/listmonk/status",
            "/v1/newsletter-studio/listmonk/send", "/v1/newsletter-studio/listmonk/drafts",
            "/v1/newsletter-studio/bridge/send", "/v1/newsletter-studio/bridge/schedule",
            "/v1/newsletter-studio/bridge/subscribers/import",
            "/v1/media/health", "/v1/newsletter-studio/bridge/drafts",
        ):
            assert client.get(path).status_code in (404, 405), path
        assert client.post("/v1/newsletter-studio/bridge/drafts").status_code == 401
        raw, headers = synthetic_request(env)
        accepted = client.post("/v1/newsletter-studio/bridge/drafts", content=raw, headers=headers)
        assert accepted.status_code == 201, accepted.text
        assert accepted.json()["sent"] is False
        assert len(calls) == 1
        assert client.post("/v1/newsletter-studio/listmonk/send", content=raw, headers=headers).status_code == 404


def test_gateway_stays_disabled_unless_all_flags_are_on(configured, monkeypatch):
    env, calls = configured
    raw, headers = synthetic_request(env)
    with TestClient(app) as client:
        monkeypatch.setenv("SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED", "0")
        assert client.post("/v1/newsletter-studio/bridge/drafts", content=raw, headers=headers).status_code == 503
        monkeypatch.setenv("SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED", "1")
        monkeypatch.setenv("SCEC_ENV", "production")
        assert client.post("/v1/newsletter-studio/bridge/drafts", content=raw, headers=headers).status_code == 503
    assert not calls
