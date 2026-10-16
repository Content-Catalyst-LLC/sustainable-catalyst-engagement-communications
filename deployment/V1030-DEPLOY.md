# v10.3.0 — Mac & Contabo isolated staging deployment

Archive is FLAT at ZIP root; extract to a dedicated folder. Never change WordPress, Caddy, DNS, existing production services, databases or public ports. No live writes, messaging, deletion, login or federation.

## Mac Terminal

```bash
cd ~/Downloads
mkdir -p scec-v1030-release
unzip -oq sustainable-catalyst-engagement-communications-v10.3.0.zip -d scec-v1030-release
test -f scec-v1030-release/backend/app/tenant_authorization_v1030.py || { echo 'Missing release module'; exit 1; }
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short   # STOP if not clean; reconcile before proceeding
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/scec-v1030-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/tenant_authorization_v1030.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.3.0.md RELEASE-CHECKSUMS-v10.3.0.json deployment/V1030-DEPLOY.md
git diff --cached --stat
git commit -m 'Build v10.3.0 Tenant Isolation and Permission Enforcement'
git push origin main
```

Expected: 278 tests, preflight PASS, version 10.3.0, production certified false. Check staged file list carefully before commit; do not ignore unexpected untracked files.

## Contabo staging, AFTER successful GitHub push

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1030
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1030/repository
cd /opt/scec-v1030/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd ..
python3 certification/certify.py
```

Expected: 278 tests and source preflight PASS.

## Temporary localhost smoke test (on Contabo)

First verify 8832 is free (`sudo ss -ltnp '( sport = :8832 )'`). If occupied, inspect the existing process; do not kill unknown services.

```bash
cd /opt/scec-v1030/repository/backend
source .venv/bin/activate
SCEC_TENANT_CERT_STAGING_ENABLED=0 \
SCEC_IDENTITY_CERT_STAGING_ENABLED=0 \
SCEC_SHELL_STAGING_ENABLED=0 \
SCEC_HUMAN_AUTH_ENABLED=0 \
SCEC_PERSISTENCE_ENABLED=0 \
SCEC_OUTBOUND_ENABLED=0 \
SCEC_DELETION_ENABLED=0 \
SCEC_FEDERATION_ENABLED=0 \
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8832
```

Open another **SSH session on Contabo** and run:

```bash
curl -fsS http://127.0.0.1:8832/health
echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8832/v1/tenant-authorization/status
```

Expected: health HTTP 200 with version `10.3.0`, phase `tenant-isolation-permission-enforcement-staging`; protected status HTTP 503 (or 401 if service bearer authentication is evaluated first). Stop temporary Uvicorn using Ctrl+C in the first Contabo SSH session. No public exposure or automatic production promotion.
