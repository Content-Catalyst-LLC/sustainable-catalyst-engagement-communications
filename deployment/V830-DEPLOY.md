# v8.3.0 — safe deployment

This release provides **opt-in** service-to-service creation and retrieval for organizations, contacts, inquiries, and engagement events. It does not ingest WordPress automatically. Authentication uses the existing service bearer token and a **static organization allowlist**; it is not a general multi-tenant end-user authorization system.

## Mac: build, test, push

Use clean Git checkout at `~/Projects/sustainable-catalyst-engagement-communications`, not Downloads. Extract v8.3.0 ZIP, rsync the folder into checkout, run `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && PYTHONPATH=. pytest -q`. From repository root run `git add . && git diff --cached --check && git commit -m 'Build v8.3.0 Contact and Engagement Python Migration' && git push origin main`.

## VPS: backend first, without disturbing v8.2

1. `sudo mkdir -p /opt/scec-v830 && sudo chown catalystadmin:catalystadmin /opt/scec-v830`
2. `git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v830/repository` (use your configured GitHub SSH URL if required)
3. `cd /opt/scec-v830/repository/backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && PYTHONPATH=. pytest -q`
4. Create a new root-protected `/etc/sustainable-catalyst/engagement/v830.env` based on v820/v800 settings, with `SCEC_ENV=production`, `SCEC_AUTH_MODE=token`, service bearer token, `SCEC_PERSISTENCE_ENABLED=0`, and **do not store DB credentials in git**.
5. Ensure `SCEC_DATABASE_URL` targets **only** the dedicated `scec_engagement_v820` PostgreSQL database. An application role with scoped permissions should be provisioned separately from the migration-owner role before write enablement.
6. **Before migration**: `sudo -u postgres pg_dump -Fc scec_engagement_v820 > ~/scec-backups/v820/pre-v830.dump` (from catalystadmin shell, with backup directory mode 700); check archive using `pg_restore -l`, rehearse restore in new scratch database. Verify `PYTHONPATH=. alembic -c alembic.ini current` is `820_001`.
7. With secure DB URL in your **shell environment only**: `PYTHONPATH=. alembic -c alembic.ini upgrade head` then `PYTHONPATH=. alembic -c alembic.ini current` should show `830_001`.
8. Create service `scec-v830` running `app.main:app` on localhost port `8813`, using v830.env, keeping existing v810 and v820 services.
9. Verify `/health` reports `8.3.0`, protected routes return HTTP 401 without bearer token; persistence routes return HTTP 503 while disabled. Test only synthetic records after setting dedicated DB role, allowlisted org UUID, and `SCEC_PERSISTENCE_ENABLED=1`.
10. Backup post-migration DB, rehearse restoration, and certify schema/audit and tenant isolation before any WordPress integration.

## Endpoint contracts

* `POST /v1/engagement/organizations|contacts|inquiries|engagement_events`
* `GET /v1/engagement/{kind}` with limit/offset
* `GET /v1/engagement/{kind}/{uuid}`

Headers: `Authorization: Bearer <service-token>` and `X-SCEC-Organization-ID: <allowlisted-uuid>`. The first organization must be created with `id` equal to the allowlisted organization UUID. Contact marketing consent defaults false. No delete/update endpoints. Existing cases and media remain out of scope.

**Known limitations:** static service-level tenant allowance is intended only for trusted backend calls, not browser users. Record email addresses are sensitive; ensure upstream rate limits, access logs avoid bodies, and credentials remain protected. Legacy exports and reconciliation are planned for later supervised migration, not yet performed.
