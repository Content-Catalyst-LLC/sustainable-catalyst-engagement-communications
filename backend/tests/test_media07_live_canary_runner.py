"""MEDIA-07.3 offline checks for the on-host live acceptance runner.

No network, email, subscriber changes, or live listmonk credentials.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "deploy/media07/accept-live-draft-canary.py"
spec = importlib.util.spec_from_file_location("media07_live_canary", SCRIPT)
canary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canary)


def test_fixture_is_synthetic_and_hash_binds_rendered_html():
    doc = canary.synthetic_payload()
    assert doc["title"].startswith("[SYNTHETIC]")
    assert doc["subject"].startswith("[SYNTHETIC]")
    assert doc["synthetic_only"] is True
    assert doc["newsletter_ref"] == "wp-newsletter:7003"
    assert len(doc["rendered_html_sha256"]) == 64
    assert "@" not in doc["body_html"]
    assert "send" not in doc and "schedule" not in doc and "lists" not in doc


def test_api_credential_fails_closed_on_world_readable_or_symlink(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text('{"username":"sc_media07_drafts","token":"fake-synthetic-credential-123456789"}')
    path.chmod(0o644)
    with pytest.raises(RuntimeError, match="0600"):
        canary.credential(path)
    path.chmod(0o600)
    assert canary.credential(path)[0] == "sc_media07_drafts"
    link = tmp_path / "auth-link.json"
    link.symlink_to(path)
    with pytest.raises(RuntimeError, match="nonsymlink"):
        canary.credential(link)


def test_wrong_api_username_is_rejected(tmp_path):
    path = tmp_path / "auth.json"
    path.write_text('{"username":"tahmad","token":"fake-synthetic-credential-123456789"}')
    path.chmod(0o600)
    with pytest.raises(RuntimeError, match="dedicated"):
        canary.credential(path)


@pytest.mark.parametrize("count,kind,expected_failure", [
    (0, "private", False),
    (1, "private", True),
    (0, "public", True),
])
def test_private_list_exact_metadata_required(count, kind, expected_failure):
    def handler(req):
        assert req.method == "GET" and req.url.path == "/api/lists/4"
        return httpx.Response(200, json={"data": {
            "id": 4, "name": canary.LIST_NAME, "type": kind,
            "status": "active", "subscriber_count": count,
        }})
    with httpx.Client(base_url=canary.LISTMONK, transport=httpx.MockTransport(handler)) as client:
        if expected_failure:
            with pytest.raises(RuntimeError, match="NO-GO"):
                canary.verified_list(client, 4)
        else:
            assert canary.verified_list(client, 4) == 4


def test_default_preflight_has_no_campaign_post(tmp_path, monkeypatch, capsys):
    path = tmp_path / "auth.json"
    path.write_text('{"username":"sc_media07_drafts","token":"fake-synthetic-credential-123456789"}')
    path.chmod(0o600)
    operations = []
    def handler(request):
        operations.append((request.method, request.url.path))
        assert request.method == "GET", "read-only preflight must not write"
        if request.url.path == "/api/lists":
            return httpx.Response(200, json={"data": {"results": [{
                "id": 4, "name": canary.LIST_NAME, "type": "private",
                "status": "active", "subscriber_count": 0,
            }]}})
        if request.url.path == "/api/lists/4":
            return httpx.Response(200, json={"data": {
                "id": 4, "name": canary.LIST_NAME, "type": "private",
                "status": "active", "subscriber_count": 0,
            }})
        if request.url.path == "/api/campaigns":
            return httpx.Response(200, json={"data": {"results": [], "total": 0}})
        if request.url.path == "/api/v1/messages":
            return httpx.Response(200, json={"total": 1, "messages": []})
        raise AssertionError("Unexpected endpoint: " + request.url.path)

    original = canary.httpx.Client
    def fake_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)
    monkeypatch.setattr(canary.httpx, "Client", fake_client)
    args = SimpleNamespace(credential_file=path, list_id=None, execute=False,
                           roles_reviewed=False, synthetic_acknowledged=False)
    canary.run(args)
    output = capsys.readouterr().out
    assert "PREFLIGHT_PASS" in output
    assert "READ_ONLY" in output
    assert operations == [
        ("GET", "/api/lists"), ("GET", "/api/lists/4"),
        ("GET", "/api/v1/messages"), ("GET", "/api/campaigns"),
    ]


def test_authentic_inprocess_routes_deny_all_delivery_operations(monkeypatch, tmp_path):
    """Before a live POST, prove all public-sounding delivery routes return 503.

    The FastAPI app runs in-process; no HTTP provider call is made.
    """
    from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
    for name in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS):
        monkeypatch.setenv(name, "0")
    for name in ("SCEC_MEDIA07_STAGING_ENABLED", "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED",
                 "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SCEC_ENV", "staging")
    monkeypatch.setenv("SCEC_IDENTITY_MODE", "bound")
    creds = tmp_path / "auth.json"
    creds.write_text('{"username":"sc_media07_drafts","token":"fake-synthetic-credential-123456789"}')
    creds.chmod(0o600)
    config = canary.enter_local_test_environment(4, creds)
    canary.assert_delivery_endpoints_blocked(config)
