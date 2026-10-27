# v11.6 isolated staging — never production activation

Do not modify production WordPress/pages/URLs, Docker, Caddy, DNS, databases or running services. No human login, real subscriptions, sending, publishing, deletion, federation or scheduled delivery. All seven live acceptance gates remain pending.

## Mac
From a clean release checkout, create a dedicated sibling virtual environment and install the existing requirements:

```sh
python3 -m venv ../scec-v1160-venv
../scec-v1160-venv/bin/python -m pip install -r backend/requirements-lock-v1130.txt
(cd backend && PYTHONPATH=. ../../scec-v1160-venv/bin/python -m pytest -q -o addopts="")
../scec-v1160-venv/bin/python certification/certify.py
git diff --check
```

Compare frontend/, wordpress-bridge/, backend/alembic/ and backend/alembic.ini against baseline f58b4a7d43908c998c5b232c311cd30eda4dc00d (15 historical protected files plus additional configuration). Verify every RELEASE-CHECKSUMS-v11.6.0.json entry and actual ZIP member. Review the diff, commit only release files, push normally, then record the actual SHA; never force-push.

## Contabo

Owner-approved exception: catalystadmin cannot create new /opt folders without an administrator. This release uses the owner-approved user-owned staging approach in a new, separate release directory. No sudo, production Docker operation or privilege workaround is needed.
Inspect /home/catalystadmin/scec-v1160/repository and port 8845 before creating anything. If either is occupied, preserve and review it, never stop an unrelated process or overwrite a checkout. When absent, create /home/catalystadmin/scec-v1160 owned by the existing staging operator, clone the reviewed branch and checkout its exact SHA in detached mode. No production credential or migration is required.

```sh
cd /home/catalystadmin/scec-v1160/repository
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-lock-v1130.txt
(cd backend && PYTHONPATH=. .venv/bin/python -m pytest -q -o addopts="")
backend/.venv/bin/python certification/certify.py
ss -ltnp '( sport = :8845 )'
```

Use the reproducible isolated verifier tools/verify_staging.py with the expected release SHA, version, phase and port. It sanitizes the process environment, explicitly disables all discovered SCEC_*ENABLED flags, binds only 127.0.0.1, uses an ephemeral service token solely for negative checks, terminates only its owned temporary process and verifies no LISTEN socket remains. Expected health HTTP 200: version 11.6.0, phase events-webinar-distribution-staging. Events status: 401 without credentials, 503 after temporary service authentication. No background process may remain.

## Artifacts and rollback
Run tools/package_release.py to hash all bundled source except the checksum manifest itself and create the complete ZIP excluding VCS, venv, secrets and caches. An external checksum file covers the manifest and ZIP. Verify actual archive bytes, not only the source directory.

Rollback is stopping the owned temporary server and retaining the preceding v11.5 source/checkout. No production release, schema or proxy changed, so no production rollback operation is needed. Never delete someone else's staging directory. Close v11.6 staging only after Mac and Contabo full suites, source preflight, protected hashes, HTTP and shutdown evidence pass. Do not begin v11.7 earlier.

The lock file records the full dependency resolution used for this release. Both Mac and isolated Contabo must pass against it; no original development environment is required. No new runtime dependency was introduced.
