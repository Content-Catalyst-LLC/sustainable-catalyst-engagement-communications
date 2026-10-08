# Sustainable Catalyst Engagement & Communications — v8.0.0

**Unified Platform Foundation** — additive release defining independent product identity, Python FastAPI application, nine domain boundaries, versioned interchange contracts, read-only capability discovery, validation-only handoff endpoint, and production startup authentication guard.

This is a foundation, **not a migrated application**. No database, frontend, WordPress plugin, newsletter delivery, test or assessment runtime is claimed. Both incumbent plugins and the existing support backend must stay running.

## macOS test

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q
```

## Development server

```bash
cd backend
source .venv/bin/activate
SCEC_ENV=development PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8810
# another terminal: curl http://127.0.0.1:8810/health
```

## VPS gated smoke test (no production cutover)

Install separately in `/opt/scec-v800`; never overwrite existing installations:

```bash
cd /opt/scec-v800/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=. .venv/bin/python -m pytest -q
export SCEC_ENV=production
export SCEC_AUTH_MODE=token
export SCEC_SERVICE_TOKEN="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')"
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8810
```

Port 8810 is an example; confirm it is free. Keep bound to localhost; configure a reverse proxy, TLS and persisted secrets in a subsequent deployment release. A generated token exported in a shell is only suitable for a temporary local smoke test. Do not expose this proof-of-foundation service publicly. No reverse proxy, production service, database migration or WordPress change is included.
