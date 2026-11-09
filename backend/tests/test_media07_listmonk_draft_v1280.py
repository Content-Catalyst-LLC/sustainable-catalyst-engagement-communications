"""MEDIA-07.3 synthetic draft adapter acceptance; no network and no real subscribers."""
import hashlib
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.identity import mint_token
from app.media07_listmonk_draft_v1280 import DraftCandidate, _credentials
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

ORG = "00000000-0000-4000-8000-000000000001"
OTHER = "00000000-0000-4000-8000-000000000002"
HTML = "<html><body><h1>Synthetic Sustainable Catalyst bulletin</h1></body></html>"
BASE = "/v1/newsletter-studio/listmonk"


def payload(**overrides):
    candidate = {
        "schema_version": "scec.media07.listmonk-draft/1",
        "organization_id": ORG,
        "newsletter_ref": "wp-newsletter:12",
        "studio_revision_sha256": "a" * 64,
        "rendered_html_sha256": hashlib.sha256(HTML.encode()).hexdigest(),
        "title": "Synthetic Research Bulletin",
        "subject": "Synthetic evidence bulletin",
        "preheader": "Staging only",
        "body_html": HTML,
        "altbody": "Synthetic test newsletter. Not to be delivered.",
        "synthetic_only": True,
    }
    return candidate | overrides


@pytest.fixture
def env(monkeypatch):
    for flag in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS):
        monkeypatch.setenv(flag, "0")
    monkeypatch.setenv("SCEC_ENV", "staging")
    monkeypatch.setenv("SCEC_IDENTITY_MODE", "bound")
    monkeypatch.setenv("SCEC_IDENTITY_SIGNING_KEY", "this_is_only_an_ephemeral_synthetic_test_key_1234567")
    monkeypatch.setenv("SCEC_ALLOWED_ORGANIZATION_IDS", ORG)
    monkeypatch.setenv("SCEC_MEDIA07_STAGING_ENABLED", "1")
    monkeypatch.setenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED", "1")
    monkeypatch.setenv("SCEC_MEDIA07_DRAFT_ORGANIZATION_ID", ORG)
    monkeypatch.setenv("SCEC_MEDIA07_EMPTY_LIST_ID", "7")
    monkeypatch.delenv("SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE", raising=False)
    return TestClient(app)


def headers(roles=("administrator",), org=ORG):
    token = mint_token(subject="media07:synthetic-test", organization_id=org,
                       roles=roles, expires_at=int(time.time()) + 60,
                       secret="this_is_only_an_ephemeral_synthetic_test_key_1234567")
    return {"Authorization": "Bearer " + token, "X-SCEC-Organization-ID": org}


def fake_provider(monkeypatch, *, subscribers=0, list_type="private", preexisting=None,
                  result_status="draft", raise_network=False):
    import app.media07_listmonk_draft_v1280 as mod
    requests = []

    def dispatch(req: httpx.Request) -> httpx.Response:
        requests.append((req.method, req.url.path, dict(req.url.params)))
        if raise_network:
            raise httpx.ConnectError("synthetic connection failure", request=req)
        if req.method == "GET" and req.url.path == "/api/lists/7":
            return httpx.Response(200, json={"data": {
                "id": 7, "name": "SCEC MEDIA07 STAGING EMPTY",
                "type": list_type, "status": "active",
                "subscriber_count": subscribers,
            }})
        if req.method == "GET" and req.url.path == "/api/campaigns":
            result = [] if preexisting is None else [preexisting]
            return httpx.Response(200, json={"data": {"results": result, "total": len(result)}})
        if req.method == "POST" and req.url.path == "/api/campaigns":
            body = json.loads(req.content)
            assert body["lists"] == [7]
            assert body["content_type"] == "html"
            assert body["type"] == "regular"
            assert body["messenger"] == "email"
            assert body["subject"].startswith("STAGING ONLY — ")
            assert "send_at" not in body and "status" not in body
            assert body["tags"] == ["scec-media07-staging", "synthetic-empty-list"]
            return httpx.Response(200, json={"data": {
                "id": 45, "name": body["name"], "status": result_status,
            }})
        raise AssertionError("Forbidden external operation: " + str(req.method) + " " + str(req.url))

    # Each request gets its own properly closed client with a strict fixed origin.
    monkeypatch.setattr(mod, "_client", lambda: httpx.Client(
        base_url="http://127.0.0.1:18898", trust_env=False,
        follow_redirects=False, transport=httpx.MockTransport(dispatch),
    ))
    return requests


def test_status_requires_real_bound_service_identity_and_enabled_flag(env, monkeypatch):
    assert env.get(BASE + "/status").status_code == 401
    assert env.get(BASE + "/status", headers=headers(("viewer",))).status_code == 403
    status = env.get(BASE + "/status", headers=headers())
    assert status.status_code == 200
    assert status.json()["external_sending_enabled"] is False
    assert status.json()["production_certified"] is False
    monkeypatch.setenv("SCEC_MEDIA07_STAGING_ENABLED", "0")
    assert env.get(BASE + "/status", headers=headers()).status_code == 503


def test_draft_creates_only_one_synthetic_campaign_without_send(env, monkeypatch):
    actions = fake_provider(monkeypatch)
    result = env.post(BASE + "/drafts", json=payload(), headers=headers())
    assert result.status_code == 201, result.text
    doc = result.json()
    assert doc["campaign_status"] == "draft"
    assert doc["campaign_id"] == 45
    assert doc["draft_reused"] is False
    assert doc["synthetic_only"] is True
    assert doc["sent"] is False
    assert [x[:2] for x in actions] == [
        ("GET", "/api/lists/7"),
        ("GET", "/api/campaigns"),
        ("POST", "/api/campaigns"),
    ]
    assert all("/status" not in path and "/test" not in path for _, path, _ in actions)
    assert env.post(BASE + "/send", headers=headers()).status_code == 503
    assert env.post(BASE + "/schedule", headers=headers()).status_code == 503
    assert env.post(BASE + "/test-send", headers=headers()).status_code == 503
    assert env.post(BASE + "/subscribers/import", headers=headers()).status_code == 503
    assert env.put(BASE + "/campaigns/45/status", headers=headers()).status_code in (404, 405)


def test_known_draft_is_reused_not_posted(env, monkeypatch):
    from app.media07_listmonk_draft_v1280 import DraftCandidate, _fingerprint
    req = DraftCandidate(**payload())
    digest = _fingerprint(ORG, req)
    prior = {"id": 15, "status": "draft", "name": "SCEC MEDIA07 STAGING " + digest}
    actions = fake_provider(monkeypatch, preexisting=prior)
    out = env.post(BASE + "/drafts", json=payload(), headers=headers())
    assert out.status_code == 201
    assert out.json()["draft_reused"] is True and out.json()["campaign_id"] == 15
    assert not any(method == "POST" for method, _, _ in actions)


@pytest.mark.parametrize("changes", [
    {"rendered_html_sha256": "b" * 64},
    {"synthetic_only": False},
    {"recipient": "someone@example.com"},
    {"lists": [1, 2]},
    {"send_at": "2026-11-10T10:00:00Z"},
    {"body_html": "<script>alert('x')</script>" + HTML},
    {"body_html": "<a href='javascript:alert(1)'>oops</a>" + HTML},
    {"body_html": "<h1>{{ .Subscriber.Email }}</h1>" + HTML},
    {"newsletter_ref": "../../etc/passwd"},
])
def test_unapproved_inputs_are_rejected(changes):
    with pytest.raises(ValidationError):
        DraftCandidate(**payload(**changes))


def test_cross_tenant_denied_and_no_api_call(env, monkeypatch):
    actions = fake_provider(monkeypatch)
    assert env.post(BASE + "/drafts", json=payload(organization_id=OTHER),
                    headers=headers()).status_code == 403
    assert env.post(BASE + "/drafts", json=payload(), headers=headers(org=OTHER)).status_code == 403
    assert env.post(BASE + "/drafts", json=payload(), headers=headers(("viewer",))).status_code == 403
    assert not actions


def test_empty_private_list_is_mandatory(env, monkeypatch):
    for kwargs in ({"subscribers": 1}, {"list_type": "public"}):
        actions = fake_provider(monkeypatch, **kwargs)
        out = env.post(BASE + "/drafts", json=payload(), headers=headers())
        assert out.status_code == 409
        assert [x[0] for x in actions] == ["GET"]


def test_sending_stays_blocked_if_adapter_opted_out(env, monkeypatch):
    actions = fake_provider(monkeypatch)
    monkeypatch.setenv("SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED", "0")
    assert env.post(BASE + "/drafts", json=payload(), headers=headers()).status_code == 503
    assert not actions


def test_provider_failure_is_sanitized(env, monkeypatch):
    actions = fake_provider(monkeypatch, raise_network=True)
    result = env.post(BASE + "/drafts", json=payload(), headers=headers())
    assert result.status_code == 502
    assert "synthetic connection failure" not in result.text
    assert len(actions) == 1


def test_api_token_file_is_private_and_not_echoed(tmp_path, monkeypatch):
    tokenfile = tmp_path / "listmonk-api.json"
    tokenfile.write_text(json.dumps({"username": "media07-fixture", "token": "only-example-token-0123456789"}))
    monkeypatch.setenv("SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE", str(tokenfile))
    tokenfile.chmod(0o644)
    with pytest.raises(Exception) as exc:
        _credentials()
    assert exc.value.status_code == 503
    tokenfile.chmod(0o600)
    assert _credentials() == ("media07-fixture", "only-example-token-0123456789")


def test_released_or_running_existing_campaign_is_not_reused(env, monkeypatch):
    from app.media07_listmonk_draft_v1280 import DraftCandidate, _fingerprint
    req = DraftCandidate(**payload())
    digest = _fingerprint(ORG, req)
    fake_provider(monkeypatch, preexisting={
        "id": 15, "status": "running", "name": "SCEC MEDIA07 STAGING " + digest,
    })
    assert env.post(BASE + "/drafts", json=payload(), headers=headers()).status_code == 409


def test_upstream_create_must_report_draft(env, monkeypatch):
    fake_provider(monkeypatch, result_status="running")
    assert env.post(BASE + "/drafts", json=payload(), headers=headers()).status_code == 502
