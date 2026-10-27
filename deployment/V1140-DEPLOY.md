# v11.4 isolated staging — never production activation

Do not modify production WordPress/pages/URLs, Docker, Caddy, DNS, databases or running services. No human login, real subscriptions, sending, publishing, deletion, federation or scheduled delivery. All seven live acceptance gates remain pending.

## Mac
From a clean release checkout, create a dedicated sibling virtual environment and install the existing requirements:

```sh
python3 -m venv ../scec-v1140-venv
../scec-v1140-venv/bin/python -m pip install -r backend/requirements-lock-v1130.txt
(cd backend && PYTHONPATH=. ../../scec-v1140-venv/bin/python -m pytest -q -o addopts="")
../scec-v1140-venv/bin/python certification/certify.py
git diff --check
```

Compare frontend/, wordpress-bridge/, backend/alembic/ and backend/alembic.ini against baseline 12f58a3ad3ac1779b0045f1cb36acdcdcc74a920 (15 historical protected files plus additional configuration). Verify every RELEASE-CHECKSUMS-v11.4.0.json entry and actual ZIP member. Review the diff, commit only release files, push normally, then record the actual SHA; never force-push.

## Contabo

Owner-approved exception: catalystadmin cannot create new /opt folders without an administrator. This release uses the owner-approved user-owned staging approach in a new, separate release directory. No sudo, production Docker operation or privilege workaround is needed.
Inspect /home/catalystadmin/scec-v1140/repository and port 8843 before creating anything. If either is occupied, preserve and review it, never stop an unrelated process or overwrite a checkout. When absent, create /home/catalystadmin/scec-v1140 owned by the existing staging operator, clone the reviewed branch and checkout its exact SHA in detached mode. No production credential or migration is required.

```sh
cd /home/catalystadmin/scec-v1140/repository
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-lock-v1130.txt
(cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q -o addopts="")
backend/.venv/bin/python certification/certify.py
ss -ltnp '( sport = :8843 )'
```

Use the reproducible isolated verifier tools/verify_staging.py with the expected release SHA, version, phase and port. It sanitizes the process environment, explicitly disables all discovered SCEC_*ENABLED flags, binds only 127.0.0.1, uses an ephemeral service token solely for negative checks, terminates only its owned temporary process and verifies no LISTEN socket remains. Expected health HTTP 200: version 11.4.0, phase media-relations-press-outreach-staging. Research-alert status: 401 without credentials, 503 after temporary service authentication. No background process may remain.

## Artifacts and rollback
Run tools/package_release.py to hash all bundled source except the checksum manifest itself and create the complete ZIP excluding VCS, venv, secrets and caches. An external checksum file covers the manifest and ZIP. Verify actual archive bytes, not only the source directory.

Rollback is stopping the owned temporary server and retaining the preceding v11.2 source/checkout. No production release, schema or proxy changed, so no production rollback operation is needed. Never delete someone else's staging directory. Close v11.4 staging only after Mac and Contabo full suites, source preflight, protected hashes, HTTP and shutdown evidence pass. Do not begin v11.5 earlier.

The lock file records the full dependency resolution used for this release. Both Mac and isolated Contabo must pass against it; no original development environment is required. No new runtime dependency was introduced.
