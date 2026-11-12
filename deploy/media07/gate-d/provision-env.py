#!/usr/bin/env python3
"""One-time Gate D synthetic-only canary environment provisioner.

Never prints secrets, never replaces a file, never starts a service or sends.
Operator must review/approve role grants and private HTTPS ingress separately.
"""
import argparse
import os
from pathlib import Path
import secrets
import stat
import sys

ORG = "00000000-0000-4000-8000-000000000007"

def provision(target):
    directory = target.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    st = directory.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or (st.st_mode & 0o077):
        raise RuntimeError("Private directory must belong to current user and deny group/world access")
    cred = directory / "listmonk-draft-credential.json"
    if not cred.exists() or cred.is_symlink() or stat.S_IMODE(cred.stat().st_mode) != 0o600:
        raise RuntimeError("Existing restricted API credential missing or insecure")
    data = {
        "SCEC_ENV": "staging",
        "SCEC_IDENTITY_MODE": "bound",
        "SCEC_MEDIA07_STAGING_ENABLED": "1",
        "SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED": "1",
        "SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED": "1",
        "SCEC_ALLOWED_ORGANIZATION_IDS": ORG,
        "SCEC_MEDIA07_DRAFT_ORGANIZATION_ID": ORG,
        "SCEC_MEDIA07_EMPTY_LIST_ID": "3",
        "SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE": str(cred),
        "SCEC_IDENTITY_SIGNING_KEY": secrets.token_urlsafe(48),
        "SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY": secrets.token_urlsafe(48),
    }
    payload = "".join(f"{key}={value}\n" for key, value in data.items())
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write("# MEDIA-07.3 synthetic staging canary only; protect as a secret.\n")
            stream.write(payload)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    print(f"GATE_D_PRIVATE_ENV_CREATED path={target} mode=0600")
    print("No service started; no endpoint exposed; transfer only the scoped HMAC key through a secure credential channel.")


if __name__ == "__main__":
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--provision-synthetic-staging", action="store_true",
                     help="Explicitly create private file once, never overwrite")
    opts = arg.parse_args()
    if not opts.provision_synthetic_staging:
        raise SystemExit("NO-GO: add --provision-synthetic-staging after private role/ingress review")
    try:
        provision(Path.home() / "media07-private/gate-d.env")
    except (OSError, RuntimeError) as exc:
        print("GATE_D_PRIVATE_ENV_NO_GO: " + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
