#!/usr/bin/env python3
"""MEDIA-07.3 private Contabo live-provider acceptance.

Run only from the checked-out backend source on the Contabo host. No public
listener, Docker restart, email, subscriber mutation, or real content.
Preflight is READ ONLY; a draft POST requires two explicit operator opt-ins.
The logged receipt never includes authentication secrets or newsletter content.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import time
from datetime import datetime, timezone

import httpx

LIST_NAME = "SCEC MEDIA07 STAGING EMPTY"
TEST_ORG = "00000000-0000-4000-8000-000000000007"
TEST_HTML = "<html><body><h1>[SYNTHETIC] MEDIA-07.3 Canary</h1><p>Test fixture only. No mailing.</p></body></html>"
TEST_SUBJECT = "[SYNTHETIC] MEDIA-07.3 Draft-Only Acceptance"
TEST_TITLE = "[SYNTHETIC] MEDIA-07.3 Canary"
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
LISTMONK = "http://127.0.0.1:18898"
MAILPIT = "http://127.0.0.1:18899"
NO_REDIRECTS = dict(timeout=httpx.Timeout(5.0), trust_env=False, follow_redirects=False)
DEFAULT_CREDENTIAL = Path.home() / "media07-private/listmonk-draft-credential.json"


def fail(message: str):
    raise RuntimeError(message)


def credential(path: Path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
        fail("API credential must be an existing nonsymlink regular file with mode 0600")
    if info.st_uid != os.geteuid() or info.st_size > 4096:
        fail("API credential owner/size invalid; run as the file owner")
    obj = json.loads(path.read_text())
    if set(obj) != {"username", "token"} or obj["username"] != "sc_media07_drafts":
        fail("Credential is not the dedicated sc_media07_drafts account")
    if (not isinstance(obj["token"], str) or not 16 <= len(obj["token"]) <= 512
            or any(ch in obj["token"] for ch in "\\r\\n")):
        fail("Credential token is malformed")
    return obj["username"], obj["token"]


def extract(response, label):
    if response.status_code not in (200, 201) or len(response.content) > 512000:
        fail(label + " rejected: HTTP " + str(response.status_code))
    try:
        payload = response.json()
    except ValueError:
        fail(label + " returned non-JSON")
    if not isinstance(payload, dict) or "data" not in payload:
        fail(label + " returned unexpected JSON")
    return payload["data"]


def verified_list(client, selected):
    if selected is None:
        data = extract(client.get("/api/lists", params={"query": LIST_NAME, "per_page": "all"}), "list discovery")
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            fail("list discovery result malformed")
        matches = [x for x in data["results"] if isinstance(x, dict) and x.get("name") == LIST_NAME]
        if len(matches) != 1:
            fail("expected exactly one named private synthetic list; use --list-id after checking admin UI")
        selected = matches[0].get("id")
    if type(selected) is not int or not 0 < selected <= 100000000:
        fail("invalid synthetic list ID")
    info = extract(client.get("/api/lists/" + str(selected)), "private list read")
    if not isinstance(info, dict) or (
        info.get("id") != selected or info.get("name") != LIST_NAME
        or info.get("type") != "private" or info.get("status") != "active"
        or type(info.get("subscriber_count")) is not int or info["subscriber_count"] != 0
    ):
        fail("NO-GO: list is not the exact active private zero-subscriber fixture")
    return selected


def mailpit_total(client):
    response = client.get("/api/v1/messages")
    if response.status_code != 200:
        fail("Mailpit baseline unavailable")
    data = response.json()
    value = data.get("total") if isinstance(data, dict) else None
    if type(value) is not int or value < 0:
        fail("Mailpit baseline invalid")
    return value


def campaign_matches(client, name):
    data = extract(
        client.get("/api/campaigns", params={"query": name, "per_page": "all"}),
        "campaign search",
    )
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        fail("campaign search unavailable")
    return [row for row in data["results"] if isinstance(row, dict) and row.get("name") == name]


def synthetic_payload():
    return {
        "schema_version": "scec.media07.listmonk-draft/1",
        "organization_id": TEST_ORG,
        "newsletter_ref": "wp-newsletter:7003",
        "studio_revision_sha256": hashlib.sha256(
            b"[SYNTHETIC] MEDIA-07.3 fixed source revision"
        ).hexdigest(),
        "rendered_html_sha256": hashlib.sha256(TEST_HTML.encode()).hexdigest(),
        "title": TEST_TITLE,
        "subject": TEST_SUBJECT,
        "preheader": "Private staging acceptance only",
        "body_html": TEST_HTML,
        "altbody": "Synthetic MEDIA-07.3 fixture only. Never send.",
        "synthetic_only": True,
    }


def enter_local_test_environment(list_id, credential_file):
    # Only this one command's process receives these ephemeral secrets.
    from uuid import UUID
    UUID(TEST_ORG)
    for name in ("SCEC_MEDIA07_STAGING_ENABLED", "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED",
                 "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED"):
        if os.environ.get(name) not in (None, "", "0"):
            fail("Refusing to inherit pre-enabled staging integration flags")
    if os.environ.get("SCEC_ENV") not in (None, "", "staging"):
        fail("Refusing non-staging inherited SCEC_ENV")
    if os.environ.get("SCEC_IDENTITY_MODE") not in (None, "", "bound"):
        fail("Refusing non-bound inherited identity")
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
    if any(os.environ.get(k, "0") != "0" for k in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS)):
        fail("Production/release danger flags are active in this shell")
    config = {
        "SCEC_ENV": "staging",
        "SCEC_IDENTITY_MODE": "bound",
        "SCEC_MEDIA07_STAGING_ENABLED": "1",
        "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED": "1",
        "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED": "1",
        "SCEC_ALLOWED_ORGANIZATION_IDS": TEST_ORG,
        "SCEC_MEDIA07_DRAFT_ORGANIZATION_ID": TEST_ORG,
        "SCEC_MEDIA07_EMPTY_LIST_ID": str(list_id),
        "SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE": str(credential_file),
        "SCEC_IDENTITY_SIGNING_KEY": secrets.token_urlsafe(48),
        "SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY": secrets.token_urlsafe(48),
    }
    os.environ.update(config)
    return config


def hmac_request(key, payload):
    from fastapi.testclient import TestClient
    from app.main import app
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    stamp = str(int(time.time()))
    sig = hmac.new(key.encode(), stamp.encode() + b"\n" + raw, hashlib.sha256).hexdigest()
    client = TestClient(app)
    return client.post(
        "/v1/newsletter-studio/bridge/drafts", content=raw,
        headers={
            "Content-Type": "application/json",
            "X-SCEC-MEDIA07-Timestamp": stamp,
            "X-SCEC-MEDIA07-Signature": sig,
        },
    )


def assert_delivery_endpoints_blocked(config):
    """These authenticated calls stay inside TestClient, NEVER at listmonk."""
    from fastapi.testclient import TestClient
    from app.identity import mint_token
    from app.main import app
    token = mint_token(
        subject="media07:synthetic-live-canary", organization_id=TEST_ORG,
        roles=("administrator",), expires_at=int(time.time()) + 60,
        secret=config["SCEC_IDENTITY_SIGNING_KEY"],
    )
    headers = {"Authorization": "Bearer " + token, "X-SCEC-Organization-ID": TEST_ORG}
    with TestClient(app) as test_client:
        for route in ("/send", "/schedule", "/test-send", "/subscribers/import", "/campaigns/1/status"):
            response = test_client.post("/v1/newsletter-studio/listmonk" + route, headers=headers)
            if response.status_code != 503:
                fail("NO-GO: forbidden newsletter route was not blocked: " + route)
        status = test_client.get("/v1/newsletter-studio/listmonk/status", headers=headers)
        if status.status_code != 200 or status.json().get("external_sending_enabled") is not False:
            fail("NO-GO: staging delivery status did not confirm sending disabled")


def run(args):
    # Do not resolve() before lstat: that would hide a credential-file symlink.
    file = Path(os.path.abspath(os.path.expanduser(str(args.credential_file))))
    user, token = credential(file)
    # The credential is read once and never logged. Listmonk stays localhost-only.
    with httpx.Client(base_url=LISTMONK, auth=(user, token), **NO_REDIRECTS) as provider, \
         httpx.Client(base_url=MAILPIT, **NO_REDIRECTS) as capture:
        list_id = verified_list(provider, args.list_id)
        before = mailpit_total(capture)
        fixture = synthetic_payload()
        # Calculate the same deterministic campaign name as the production adapter.
        if str(BACKEND) not in sys.path:
            sys.path.insert(0, str(BACKEND))
        from app.media07_listmonk_draft_v1280 import DraftCandidate, _fingerprint
        digest = _fingerprint(TEST_ORG, DraftCandidate(**fixture))
        name = "SCEC MEDIA07 STAGING " + digest
        existing = campaign_matches(provider, name)
        if len(existing) > 1 or any(row.get("status") != "draft" for row in existing):
            fail("NO-GO: ambiguous or non-draft existing campaign")
        print("PREFLIGHT_PASS list_id=" + str(list_id)
              + " subscriber_count=0 mailpit_baseline=" + str(before)
              + " exact_matching_drafts=" + str(len(existing))
              + " API_user=" + user)
        if not args.execute:
            print("READ_ONLY: no campaign created. Send and role permissions have NOT been proven.")
            return

        if not args.roles_reviewed or not args.synthetic_acknowledged:
            fail("NO-GO: operator must independently review non-send role and synthetic-only fixture")
        # No actual external HTTP service is started. FastAPI executes in-process,
        # but uses the real listmonk host-local API with the restricted credential.
        config = enter_local_test_environment(list_id, file)
        assert_delivery_endpoints_blocked(config)
        # Refuse a second simultaneous local canary writer on this host.
        lock_path = Path.home() / "media07-private" / ".media07-03-canary.lock"
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(lock_fd)
            fail("NO-GO: another MEDIA-07.3 local canary is already running")
        try:
            run_authenticated_fixture(provider, capture, list_id, fixture, digest, name, before, config, user)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
        return


def run_authenticated_fixture(provider, capture, list_id, fixture, digest, name, before, config, user):
        first = hmac_request(config["SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY"], fixture)
        if first.status_code != 201:
            fail("NO-GO: first authenticated bridge draft rejected HTTP " + str(first.status_code))
        first_doc = first.json()
        second = hmac_request(config["SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY"], fixture)
        if second.status_code != 201:
            fail("NO-GO: repeat authenticated draft rejected HTTP " + str(second.status_code))
        second_doc = second.json()
        for result in (first_doc, second_doc):
            if (result.get("campaign_status") != "draft" or result.get("sent") is not False
                    or result.get("synthetic_only") is not True
                    or result.get("fingerprint") != digest
                    or type(result.get("campaign_id")) is not int):
                fail("NO-GO: bridge returned invalid draft receipt")
        if first_doc["campaign_id"] != second_doc["campaign_id"] or second_doc.get("draft_reused") is not True:
            fail("NO-GO: duplicate reconciliation failed")
        matches = campaign_matches(provider, name)
        if len(matches) != 1 or matches[0].get("id") != first_doc["campaign_id"]:
            fail("NO-GO: expected exactly one deterministic draft")
        detail = extract(provider.get("/api/campaigns/" + str(first_doc["campaign_id"])), "draft readback")
        if (not isinstance(detail, dict) or detail.get("status") != "draft"
                or detail.get("body") != TEST_HTML or detail.get("subject") != "STAGING ONLY — " + TEST_SUBJECT
                or detail.get("altbody") != fixture["altbody"]
                or detail.get("messenger") != "email" or detail.get("content_type") != "html"
                or detail.get("sent") not in (0, None)
                or sorted(x.get("id") for x in detail.get("lists", []) if isinstance(x, dict)) != [list_id]):
            fail("NO-GO: campaign readback not an unchanged unsent synthetic draft")
        verified_list(provider, list_id)
        after = mailpit_total(capture)
        if after != before:
            fail("NO-GO: Mailpit message count changed during draft acceptance")
        receipt = {
            "release": "MEDIA-07.3",
            "result": "LIVE_PROVIDER_SYNTHETIC_DRAFT_PASS",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "in-process signed FastAPI route to real localhost listmonk; NOT deployed HTTPS or WordPress UI",
            "organization_id": TEST_ORG,
            "list_id": list_id, "subscriber_count": 0,
            "api_user": user, "role_review_operator_attested": True,
            "send_denial_programmatically_verified": False,
            "campaign_id": first_doc["campaign_id"],
            "draft_status": "draft",
            "first_reused": first_doc.get("draft_reused") is True,
            "repeat_reused": True,
            "mailpit_before": before, "mailpit_after": after,
            "sent": False, "bluehost_https_bridge_accepted": False,
        }
        dest = Path.home() / "media07-private" / "acceptance"
        dest.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(dest, 0o700)
        target = dest / "MEDIA07-03-LIVE-CANARY.json"
        temporary = dest / ("." + target.name + ".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(receipt, stream, sort_keys=True, indent=2)
                stream.write("\n")
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        print("LIVE_PROVIDER_DRAFT_PASS campaign_id=" + str(first_doc["campaign_id"])
              + " duplicate_reconciled=true mailpit_delta=0")
        print("LOCAL_RECEIPT " + str(target))
        print("NOT_ACCEPTED: independent permission denial, deployed HTTPS bridge and Bluehost Studio UI")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credential-file", type=Path, default=DEFAULT_CREDENTIAL)
    parser.add_argument("--list-id", type=int, default=None, help="Exact private synthetic list ID; auto-discover when omitted")
    parser.add_argument("--execute", action="store_true", help="Opt in to exactly one synthetic draft creation and reconciliation")
    parser.add_argument("--roles-reviewed", action="store_true", help="Operator independently verified campaigns:send and subscriber permissions are absent")
    parser.add_argument("--synthetic-acknowledged", action="store_true", help="Operator affirms fixture is synthetic, never a real publication")
    args = parser.parse_args()
    try:
        run(args)
    except Exception as exc:
        print("MEDIA07_LIVE_ACCEPTANCE_NO_GO: " + str(exc).splitlines()[0][:200], file=sys.stderr)
        raise SystemExit(1)
