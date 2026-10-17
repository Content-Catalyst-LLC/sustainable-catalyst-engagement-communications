# v10.5.0 — Mac and Contabo staging-only deployment

Do not install a new WordPress bridge, change the five public pages, change Caddy/DNS/Docker, execute Alembic, restart production workloads or enable writes/outbound/human login/federation/deletion.

## Mac

```bash
cd ~/Downloads
mkdir -p scec-v1050-release
unzip -oq sustainable-catalyst-engagement-communications-v10.5.0.zip -d scec-v1050-release
test -f scec-v1050-release/backend/app/wordpress_bridge_certification_v1050.py || exit 1
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
# Stop if there are pending changes. Confirm git pull succeeds before continuing.
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/scec-v1050-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/wordpress_bridge_certification_v1050.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.5.0.md RELEASE-CHECKSUMS-v10.5.0.json deployment/V1050-DEPLOY.md
git diff --cached --stat
git commit -m "Build v10.5.0 WordPress Intake Bridge Certification"
git push origin main
```

Expected: 322 passed; preflight PASS; production_certified false; production_writes_enabled false.

## Contabo (after successful Git push)

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1050
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1050/repository
cd /opt/scec-v1050/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8834 )'
```

Only if port 8834 is free:

```bash
cd /opt/scec-v1050/repository/backend
source .venv/bin/activate
SCEC_WORDPRESS_BRIDGE_CERT_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8834
```

Open a second Mac terminal, connect to the Contabo VPS with SSH, and execute **there**:

```bash
curl -fsS http://127.0.0.1:8834/health; echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8834/v1/wordpress-intake-certification/status
```

Expected health version 10.5.0; safety gate HTTP 503 (or 401 if identity gate runs first). Stop Uvicorn with Ctrl-C in the first session and confirm the port is free with `sudo ss -ltnp '( sport = :8834 )'`.
