# v9.0.0 — Human Authentication, Sessions & Authorization (STAGING ONLY)

## Scope

The feature is **disabled by default**. The prior v8.6 service-principal API,
frontend v8.7, and WordPress v8.8.2 remain unchanged. This build adds an opt-in
OIDC authorization-code-with-PKCE identity boundary at `/v1/human-auth/*`.
There is **no bridge from human sessions to production record-write APIs**.
Database migrations: none. Do **not** enable `SCEC_PERSISTENCE_ENABLED`.

## Deployment (Mac)

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.0.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__'   ~/Downloads/sustainable-catalyst-engagement-communications-v9.0.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
git diff --check
git add -A
git commit -m "Build v9.0.0 human authentication and session boundary"
git push origin main
```

## Deployment (Contabo: non-disruptive, loopback staged instance)

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v900
sudo install -d -m 700 -o catalystadmin -g catalystadmin /var/lib/scec-human-auth
# Clone only if this directory is empty and not already cloned:
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v900/repository
cd /opt/scec-v900/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
# Safe, disabled-by-default smoke test; no public listener
SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 PYTHONPATH=.   .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8819
```

In a **second** Contabo terminal:

```bash
curl -fsS http://127.0.0.1:8819/health
curl -s -o /dev/null -w 'disabled login HTTP %{http_code}\n' http://127.0.0.1:8819/v1/human-auth/login
```

Expected disabled login: HTTP 503. Stop the foreground Uvicorn process with Ctrl+C.
Keep v8.6 backend service `scec-v860` on port 8816 and v8.7 frontend 8097 untouched.
Do NOT point public Caddy or WordPress at port 8819.

## Identity provider enrollment — required future acceptance

Configure a **trusted OIDC provider** with authorization code + PKCE and client secret.
Registration must use a backend HTTPS callback on a deliberately restricted auth domain;
do not expose this endpoint until login/callback, cookie and origin tests pass in a browser.
Required environment settings are:

- `SCEC_HUMAN_AUTH_ENABLED=1` (leave **0** for initial deployment)
- `SCEC_OIDC_ISSUER`, `SCEC_OIDC_CLIENT_ID`, `SCEC_OIDC_CLIENT_SECRET`
- `SCEC_OIDC_AUTH_URL`, `SCEC_OIDC_TOKEN_URL`, `SCEC_OIDC_JWKS_URL`
- `SCEC_HUMAN_AUTH_ORIGIN`, `SCEC_OIDC_REDIRECT_URI` (origin + `/v1/human-auth/callback`)
- `SCEC_HUMAN_SESSION_DB=/var/lib/scec-human-auth/sessions.sqlite3`
- `SCEC_HUMAN_MEMBERSHIPS` JSON object mapping **verified OIDC subjects** to server-controlled `organization_id` UUID and `roles` arrays.
- `SCEC_PERSISTENCE_ENABLED=0`

No secret is required in the frontend, WordPress, or Git. Do not print real client secrets.
The trust issuer, auth/token endpoints, and JWKS hosts against an OIDC discovery document
before production use; current implementation consumes explicit admin-trusted URLs.
The session store is single-host SQLite, **not** a production HA session backend.

## Required independent production acceptance

1. Configure IdP and exercise real login, token validation, PKCE and nonce.
2. Verify issuer, audience, signing key rotation, clock skew, network failure handling.
3. Verify secure cookie behavior through the real HTTPS reverse proxy.
4. Verify logout, multi-session revocation, session expiration, concurrent requests.
5. Verify CSRF and cross-origin enforcement with a real browser.
6. Validate approved membership provisioning and tenant isolation for every role.
7. Build a backend-mediated, session-authorized adapter before any real records.
8. Replace staging SQLite with an operationally supported shared session store if multi-instance HA is required.
9. Complete privacy, audit retention, backup/restore and incident response review.
10. Keep production writes off until explicit authorization and persistence certification.

**v9.0.0 code-test result is not full production security certification.**
