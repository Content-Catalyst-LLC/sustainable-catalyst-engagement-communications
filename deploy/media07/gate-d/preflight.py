#!/usr/bin/env python3
"""Gate D on-host pre-start verification. Read-only; emits no secrets.

Used by a systemd --user unit before a loopback-only single-worker canary.
Only the known synthetic list ID 3 is allowed, and Mailpit is checked before
service startup. Never starts/stops or modifies a Docker container.
"""
import json
import os
import re
import stat
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS  # noqa: E402

ORG = "00000000-0000-4000-8000-000000000007"
EXPECTED = {
    "SCEC_ENV": "staging",
    "SCEC_IDENTITY_MODE": "bound",
    "SCEC_MEDIA07_STAGING_ENABLED": "1",
    "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED": "1",
    "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED": "1",
    "SCEC_ALLOWED_ORGANIZATION_IDS": ORG,
    "SCEC_MEDIA07_DRAFT_ORGANIZATION_ID": ORG,
    "SCEC_MEDIA07_EMPTY_LIST_ID": "3",
}
AUTH_USER = "sc_media07_drafts"
LIST_NAME = "SCEC MEDIA07 STAGING EMPTY"
ENV_FILE = Path.home() / "media07-private/gate-d.env"
CREDENTIAL = Path.home() / "media07-private/listmonk-draft-credential.json"


def halt(message):
    raise RuntimeError(message)


def safe_private_file(path):
    p = Path(path)
    st = p.lstat()
    if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600 or st.st_uid != os.geteuid():
        halt("private file owner/mode invalid")
    if st.st_size <= 0 or st.st_size > 4096:
        halt("private file size invalid")
    return p


def read_env_file(path):
    """Simple restricted systemd EnvironmentFile subset; disallow shell escapes."""
    result = {}
    for line in safe_private_file(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            halt("invalid key=value line in private configuration")
        key, val = line.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            halt("invalid environment key")
        if (key in result or not val or any(c.isspace() for c in val)
                or "'" in val or '"' in val or "$" in val or "\\" in val):
            halt("invalid or duplicated private setting")
        result[key] = val
    return result


def check_configuration(settings, credential_file):
    for key, required in EXPECTED.items():
        if settings.get(key) != required:
            halt("staging configuration incomplete: " + key)
    if any(settings.get(key, "0") != "0" for key in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS)):
        halt("delivery/production danger flag must be off")
    signing = settings.get("SCEC_IDENTITY_SIGNING_KEY", "")
    bridge = settings.get("SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY", "")
    if not (32 <= len(bridge) <= 512 and 32 <= len(signing) <= 512 and signing != bridge):
        halt("distinct 32+ byte HMAC and identity secrets required")
    if settings.get("SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE") != str(credential_file):
        halt("credential path must be the dedicated staging path")
    safe_private_file(credential_file)
    cred = json.loads(credential_file.read_text(encoding="utf-8"))
    if (set(cred) != {"username", "token"} or cred["username"] != AUTH_USER
            or not isinstance(cred["token"], str) or len(cred["token"]) < 16):
        halt("dedicated restricted API credential invalid")
    return cred


def check_local_backend(cred):
    with httpx.Client(
        base_url="http://127.0.0.1:18898",
        auth=(cred["username"], cred["token"]),
        timeout=6, trust_env=False, follow_redirects=False,
    ) as client:
        resp = client.get("/api/lists/3")
        if resp.status_code != 200:
            halt("restricted private list read rejected, HTTP " + str(resp.status_code))
        obj = resp.json().get("data", {})
        if (not isinstance(obj, dict) or obj.get("id") != 3
                or obj.get("name") != LIST_NAME
                or obj.get("status") != "active" or obj.get("type") != "private"
                or type(obj.get("subscriber_count")) is not int
                or obj["subscriber_count"] != 0):
            halt("NO-GO: list 3 is not empty active private staging")
    with httpx.Client(
        base_url="http://127.0.0.1:18899",
        timeout=6, trust_env=False, follow_redirects=False,
    ) as capture:
        resp = capture.get("/api/v1/messages")
        if resp.status_code != 200 or type(resp.json().get("total")) is not int:
            halt("Mailpit baseline missing")
        return resp.json()["total"]


def main():
    settings = read_env_file(ENV_FILE)
    cred = check_configuration(settings, CREDENTIAL)
    baseline = check_local_backend(cred)
    print("GATE_D_PREFLIGHT_PASS private_list_id=3 subscriber_count=0 "
          "mailpit_baseline=" + str(baseline)
          + " gateway_loopback_only=unit-configured; no send")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, httpx.HTTPError, RuntimeError) as exc:
        # Preflight errors must not echo private config values.
        msg = str(exc)
        if "token" in msg.lower() or "secret" in msg.lower():
            msg = "private configuration rejected"
        print("GATE_D_PREFLIGHT_NO_GO: " + msg[:120], file=sys.stderr)
        raise SystemExit(1)
