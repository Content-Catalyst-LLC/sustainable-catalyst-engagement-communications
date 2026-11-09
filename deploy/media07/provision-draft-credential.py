#!/usr/bin/env python3
"""Create a restricted local staging-only listmonk API credential file.

Interactive, executed ON Contabo by the authorized operator. Does not call
listmonk, alter services, accept credentials on command line, or print secrets.
"""
import getpass
import json
import os
from pathlib import Path
import re
import stat
import sys


def provision():
    if os.geteuid() == 0:
        raise RuntimeError("Run as the ordinary catalystadmin user, not root")
    root = Path.home() / "media07-private"
    root.mkdir(mode=0o700, exist_ok=True)
    if root.is_symlink() or not stat.S_ISDIR(root.stat().st_mode) or root.stat().st_mode & 0o077:
        raise RuntimeError("Private directory must be real and mode 0700")
    target = root / "listmonk-draft-credential.json"
    if target.exists() or target.is_symlink():
        raise RuntimeError("Credential file already exists; inspect or rotate separately, do not overwrite")
    username = input("Dedicated staging listmonk API username: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.@:-]{3,128}", username):
        raise RuntimeError("Invalid API username")
    token = getpass.getpass("Dedicated listmonk API token (input hidden): ")
    if not (16 <= len(token) <= 512) or any(c in token for c in "\r\n"):
        raise RuntimeError("Invalid API token")
    data = json.dumps({"username": username, "token": token}, separators=(",", ":")) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(target, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(data)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    print("Credential created privately at:", target)
    print("No service was changed and no email was sent.")


if __name__ == "__main__":
    try:
        provision()
    except (RuntimeError, OSError, EOFError, KeyboardInterrupt) as exc:
        print("MEDIA-07 credential provisioning blocked:", type(exc).__name__, file=sys.stderr)
        sys.exit(1)
