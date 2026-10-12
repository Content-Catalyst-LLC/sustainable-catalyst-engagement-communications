# v8.7.0 deployment — Mac → GitHub → Contabo

**Prerequisite:** v8.6.0 service is already running on `127.0.0.1:8816`. This is a static web foundation, not yet a login system. No live customer data is displayed, no writes, and no PostgreSQL migration.

## Mac terminal
1. Save the supplied ZIP under `~/Downloads`.
2. Run:

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v8.7.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v8.7.0/ ./
cd backend
source .venv/bin/activate
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
node --check frontend/assets/app.js
git diff --check
git status --short
git add backend frontend docs deployment README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v8.7.0.md
git diff --cached --stat
git commit -m 'Build v8.7.0 standalone web application foundation'
git push origin main
```

## Contabo server — separate standalone web

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v870
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v870/repository
cd /opt/scec-v870/repository
node --check frontend/assets/app.js  # optional: skip if node is not installed
cd frontend
docker compose -f compose.yaml up -d --build
docker compose -f compose.yaml ps
curl -fsS http://127.0.0.1:8097/healthz; echo
curl -fsS http://127.0.0.1:8097/ | grep -o 'RELEASE 8.7.0' | head -1
curl -sSI http://127.0.0.1:8097/ | grep -iE 'content-security-policy|x-frame-options|http/'
```

**Do not** expose port 8097 via firewall or configure a public DNS/Caddy host until browser presentation and security gates have been checked. The private API port 8816 remains loopback-only.

Optional v8.7 backend source certification (without changing the production v8.6 service):

```bash
cd /opt/scec-v870/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
```

There is **no need to start a second FastAPI service** for this web-only milestone. The web shell intentionally makes no API requests. The new backend version is a source-level alignment marker only.

## Rollback

```bash
cd /opt/scec-v870/repository/frontend
docker compose -f compose.yaml down
```

This leaves the previous `scec-v860` service and the PostgreSQL database unchanged.

## Explicit acceptance gates before any personal records
- Real user authentication or verified human-to-service broker, with secure HttpOnly server-side session cookies
- CSRF defenses, revocation, session expiry, security event logging and a BFF enforcing organization binding and role policies
- Actual authenticated API read, row-level tenant isolation and adversarial authorization tests
- An organizational privacy and retention policy
- Only afterward enable carefully scoped reads/writes behind a staged feature flag
