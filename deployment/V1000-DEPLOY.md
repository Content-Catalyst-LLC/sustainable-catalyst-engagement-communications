# v10.0.0 — Unified Engagement Platform: Mac / GitHub / Contabo

## Operating constraints
- No production certification; no production writes, outbound messaging, deletion, or actual federation.
- Five existing WordPress pages preserved; do not install or change the bridge.
- Do not touch unrelated Caddy/Docker/Site Intelligence, existing production processes, or database.
- This package is a static read-only frontend plus a disabled-by-default private API discovery layer, not a production CRM.

## Mac Terminal
```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v10.0.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short  # STOP unless clean
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v10.0.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/unified_v1000.py backend/tests certification/certify.py frontend/index.html frontend/assets/app.js README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.0.0.md RELEASE-CHECKSUMS-v10.0.0.json deployment/V1000-DEPLOY.md
git diff --cached --stat
git commit -m "Build v10.0.0 Unified Engagement Platform"
git push origin main
```
Expect 232 passed, preflight PASS, production_certified false.

## Contabo (after successful GitHub push)
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1000
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1000/repository
cd /opt/scec-v1000/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd /opt/scec-v1000/repository
python3 certification/certify.py
```

## Isolated localhost smoke test, no production configuration changes
```bash
cd /opt/scec-v1000/repository/backend
source .venv/bin/activate
if ss -ltn | grep -q ':8829 '; then
  echo 'Port 8829 occupied. Stop and investigate.'
else
  SCEC_UNIFIED_STAGING_ENABLED=0 \
  SCEC_ASSURANCE_STAGING_ENABLED=0 \
  SCEC_FEDERATION_STAGING_ENABLED=0 \
  SCEC_FEDERATION_ENABLED=0 \
  SCEC_PRIVACY_STAGING_ENABLED=0 \
  SCEC_ANALYTICS_STAGING_ENABLED=0 \
  SCEC_COMMUNICATIONS_STAGING_ENABLED=0 \
  SCEC_INSTITUTIONAL_STAGING_ENABLED=0 \
  SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 \
  SCEC_COMMUNITY_STAGING_ENABLED=0 \
  SCEC_INTAKE_STAGING_ENABLED=0 \
  SCEC_HUMAN_AUTH_ENABLED=0 \
  SCEC_PERSISTENCE_ENABLED=0 \
  SCEC_OUTBOUND_ENABLED=0 \
  SCEC_DELETION_ENABLED=0 \
  PYTHONPATH=. \
  .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8829 > /tmp/scec-v1000-staging.log 2>&1 &
  PID=$!
  trap 'kill "$PID" 2>/dev/null || true' EXIT
  sleep 3
  curl -fsS --max-time 5 http://127.0.0.1:8829/health
  echo
  curl -sS --max-time 5 -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8829/v1/unified-platform/status
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  trap - EXIT
  tail -20 /tmp/scec-v1000-staging.log
fi
```
Expected health: 200 with version `10.0.0` phase `unified-engagement-platform-staging`; status endpoint: 503 (intentionally disabled); clean shutdown. Note: this 503 smoke check does not independently validate every write prohibition; the automated tests cover prohibited mutation routes when staging is enabled.
