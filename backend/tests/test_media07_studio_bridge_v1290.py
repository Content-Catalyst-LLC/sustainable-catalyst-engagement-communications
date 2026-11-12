"""MEDIA-07.3 WordPress signed Studio handoff: isolated synthetic acceptance.

No real provider or network; only the explicitly gated draft adapter is called.
"""
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

ORG = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
KEY = "synthetic_separate_hmac_studio_bridge_123456789_for_tests"
HTML = "<html><body><h1>Only synthetic test content</h1></body></html>"
URL = "/v1/newsletter-studio/bridge/drafts"


def candidate(**kwargs):
    doc = dict(
        schema_version="scec.media07.listmonk-draft/1",
        organization_id=ORG,
        newsletter_ref="wp-newsletter:27",
        studio_revision_sha256="a" * 64,
        rendered_html_sha256=hashlib.sha256(HTML.encode()).hexdigest(),
        title="[SYNTHETIC] Research Bulletin",
        subject="[SYNTHETIC] Test Research Bulletin",
        preheader="Not for delivery",
        body_html=HTML,
        altbody="Only synthetic test content",
        synthetic_only=True,
    )
    return doc | kwargs


def signed(doc, key=KEY, stamp=None):
    body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
    at = str(int(time.time()) if stamp is None else stamp)
    signature = hmac.new(key.encode(), at.encode() + b"\n" + body, hashlib.sha256).hexdigest()
    return body, {
        "Content-Type": "application/json",
        "X-SCEC-MEDIA07-Timestamp": at,
        "X-SCEC-MEDIA07-Signature": signature,
    }


@pytest.fixture
def staging(monkeypatch):
    for flag in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS):
        monkeypatch.setenv(flag, "0")
    for key, val in {
        "SCEC_ENV": "staging",
        "SCEC_IDENTITY_MODE": "bound",
        "SCEC_IDENTITY_SIGNING_KEY": "another_isolated_identity_test_secret_1234567",
        "SCEC_MEDIA07_STAGING_ENABLED": "1",
        "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED": "1",
        "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED": "1",
        "SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY": KEY,
        "SCEC_ALLOWED_ORGANIZATION_IDS": ORG,
        "SCEC_MEDIA07_DRAFT_ORGANIZATION_ID": ORG,
        "SCEC_MEDIA07_EMPTY_LIST_ID": "7",
    }.items():
        monkeypatch.setenv(key, val)
    import app.media07_studio_bridge_v1290 as mod
    called = []

    def fake_create_draft(doc, tenant):
        called.append((doc, tenant))
        return {
            "release": "MEDIA-07.3", "organization_id": str(tenant),
            "campaign_id": 55, "campaign_status": "draft",
            "draft_reused": False, "fingerprint": "a" * 64,
            "synthetic_only": True, "sent": False,
        }
    monkeypatch.setattr(mod, "create_draft", fake_create_draft)
    return TestClient(app), called


def test_signed_current_saved_draft_is_only_create_path(staging):
    client, calls = staging
    body, headers = signed(candidate())
    out = client.post(URL, content=body, headers=headers)
    assert out.status_code == 201, out.text
    assert out.json()["campaign_status"] == "draft"
    assert out.json()["sent"] is False
    assert len(calls) == 1 and str(calls[0][1]) == ORG
    assert client.post(URL.replace("/drafts", "/send"), content=body, headers=headers).status_code == 404


def test_missing_or_invalid_signature_does_not_call_provider(staging):
    client, calls = staging
    body, headers = signed(candidate())
    assert client.post(URL, content=body).status_code == 401
    assert client.post(URL, content=body + b" ", headers=headers).status_code == 401
    bad = dict(headers, **{"X-SCEC-MEDIA07-Signature": "0" * 64})
    assert client.post(URL, content=body, headers=bad).status_code == 401
    assert not calls


def test_stale_timestamp_and_wrong_key_fail_closed(staging):
    client, calls = staging
    for args in ({"stamp": int(time.time()) - 500}, {"key": "wrong_separate_bridge_key_1234567890123456789"}):
        body, headers = signed(candidate(), **args)
        assert client.post(URL, content=body, headers=headers).status_code == 401
    assert not calls


@pytest.mark.parametrize("change", [
    {"organization_id": OTHER},
    {"title": "Real newsletter"},
    {"subject": "Real email"},
    {"synthetic_only": False},
    {"lists": [1]},
    {"recipient": "real@example.com"},
    {"rendered_html_sha256": "0" * 64},
])
def test_wrong_tenant_or_non_synthetic_payload_rejected(staging, change):
    client, calls = staging
    body, headers = signed(candidate(**change))
    assert client.post(URL, content=body, headers=headers).status_code in (422, 503)
    assert not calls


def test_disabled_bridge_and_danger_flags_fail_closed(staging, monkeypatch):
    client, calls = staging
    body, headers = signed(candidate())
    monkeypatch.setenv("SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED", "0")
    assert client.post(URL, content=body, headers=headers).status_code == 503
    monkeypatch.setenv("SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED", "1")
    monkeypatch.setenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED", "0")
    assert client.post(URL, content=body, headers=headers).status_code == 503
    monkeypatch.setenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED", "1")
    monkeypatch.setenv(DANGER_FLAGS[0], "1")
    assert client.post(URL, content=body, headers=headers).status_code == 503
    assert not calls


def test_identical_identity_key_rejected(staging, monkeypatch):
    client, calls = staging
    monkeypatch.setenv("SCEC_IDENTITY_SIGNING_KEY", KEY)
    body, headers = signed(candidate())
    assert client.post(URL, content=body, headers=headers).status_code == 503
    assert not calls


def test_signed_invalid_json_and_html_are_rejected(staging):
    client, calls = staging
    body, headers = signed(candidate(body_html="<script>alert(1)</script>" + HTML))
    assert client.post(URL, content=body, headers=headers).status_code == 422
    raw = b"not valid json"
    stamp = str(int(time.time()))
    sig = hmac.new(KEY.encode(), stamp.encode() + b"\n" + raw, hashlib.sha256).hexdigest()
    assert client.post(URL, content=raw, headers={
        "Content-Type": "application/json",
        "X-SCEC-MEDIA07-Timestamp": stamp,
        "X-SCEC-MEDIA07-Signature": sig,
    }).status_code == 422
    assert not calls
