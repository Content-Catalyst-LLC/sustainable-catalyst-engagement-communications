# Release v8.2.0 — isolated VPS staging

Mac (inside ~/Projects/sustainable-catalyst-engagement-communications): apply release ZIP using rsync excluding `.git`, `.venv`, run pytest, commit and push.

VPS: use a NEW database, not any legacy production database. Clone into `/opt/scec-v820/repository` after GitHub push, install Python 3.12 dependencies, run `PYTHONPATH=. python -m pytest -q`.

To generate offline SQL (no database connection, requires dedicated DB URL):

```
cd /opt/scec-v820/repository/backend
export SCEC_DATABASE_URL='postgresql+psycopg://scec_app:REPLACE@127.0.0.1:5432/scec_engagement_v820'
PYTHONPATH=. .venv/bin/alembic -c alembic.ini upgrade head --sql > /tmp/scec-v820-schema.sql
```

Review SQL before applying; only apply to the newly provisioned empty dedicated database, using a migration role with schema-create permissions. Validate `alembic current` and `alembic heads` afterward.

Service: deploy localhost-only on unused port 8812, reuse production token env and preserve `scec-v810` for rollback. **Do not** expose database internals or migration commands as APIs.
