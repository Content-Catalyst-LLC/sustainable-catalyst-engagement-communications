# v11.9.0 isolated staging — never production activation

Preserve production WordPress, five existing URLs, Docker, Caddy, DNS, databases and running services. No credentials copied, human login, subscriptions, sending, publication, deletion, federation or scheduled delivery. All seven production acceptance gates remain pending.

From a clean checkout of the reviewed release, create a sibling virtual environment:

```sh
python3 -m venv ../scec-v1190-venv
../scec-v1190-venv/bin/python -m pip install -r backend/requirements-lock-v1130.txt
(cd backend && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ../../scec-v1190-venv/bin/python -m pytest -q -o addopts="")
../scec-v1190-venv/bin/python certification/certify.py
git diff --check
```

Compare all 16 protected frontend/WordPress/migration/Alembic configuration files with predecessor `e0452613d5cee1f48fe20fa8a0bf6472517d5bf3`. Package using tools/package_release.py; verify every source manifest hash and actual ZIP member. Review, commit and push normally; record exact remote SHA. Never force-push or merge automatically.

## Contabo

Use the owner-approved user-owned staging approach: `/home/catalystadmin/scec-v1190/repository`. No sudo or production Docker workaround. Confirm both release directory absent and loopback port 8848 free; refuse to overwrite a checkout or stop an unrelated process. Clone the reviewed branch into the new dedicated directory and detach at its exact SHA. Create backend/.venv, install backend/requirements-lock-v1130.txt and repeat the complete tests and source preflight. No production credential, database or migration required.

Use tools/verify_staging.py with --root, --sha, --version 11.9.0, --phase audience-analytics-assurance-staging, --port 8848 and the documented module status route. It sanitizes the environment, disables dangerous flags, binds 127.0.0.1 only and uses an ephemeral service token for negative checks. Require health200 with exact version/phase, status401 unauthenticated and503 authenticated. Terminate only its owned process and verify no LISTEN socket remains. Independently verify every source hash on Contabo and that its checkout is clean.

## Rollback and closure

Stop only the owned temporary staging process, retain the predecessor checkout and evidence. No production schema, proxy, service or source changed; no production rollback operation is needed. Never delete unrelated staging files. Close only after full Mac/Contabo suites, source preflight, protected hashes, exact-commit HTTP/shutdown and complete archive checks pass. The successor may begin only after this closure. Dependencies reuse the captured lock; no new runtime dependency.
