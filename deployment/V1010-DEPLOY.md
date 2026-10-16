# Engagement & Communications v10.1.0 — Mac / Contabo staging

No production operations or WordPress changes. Do not alter Caddy, Docker, Site Intelligence or existing services.

## Mac
```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v10.1.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# Proceed only if clean before pull
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ ~/Downloads/sustainable-catalyst-engagement-communications-v10.1.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/application_shell_v1010.py backend/tests certification/certify.py frontend README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.1.0.md RELEASE-CHECKSUMS-v10.1.0.json deployment/V1010-DEPLOY.md
git diff --cached --stat
git commit -m "Build v10.1.0 Unified Application Shell and Navigation"
git push origin main
```

## Contabo: after Mac push succeeds
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1010
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1010/repository
cd /opt/scec-v1010/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
```

## Isolated smoke test — port 8830
```bash
cd /opt/scec-v1010/repository/backend
source .venv/bin/activate
if ss -ltn | grep -q ':8830 '; then echo 'Port occupied: STOP'; else
  SCEC_SHELL_STAGING_ENABLED=0 SCEC_UNIFIED_STAGING_ENABLED=0 SCEC_ASSURANCE_STAGING_ENABLED=0 \
  SCEC_FEDERATION_STAGING_ENABLED=0 SCEC_FEDERATION_ENABLED=0 SCEC_PRIVACY_STAGING_ENABLED=0 \
  SCEC_ANALYTICS_STAGING_ENABLED=0 SCEC_COMMUNICATIONS_STAGING_ENABLED=0 \
  SCEC_INSTITUTIONAL_STAGING_ENABLED=0 SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 \
  SCEC_COMMUNITY_STAGING_ENABLED=0 SCEC_INTAKE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 \
  SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 \
  PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8830 > /tmp/scec-v1010.log 2>&1 &
  PID=$!
  trap 'kill "$PID" 2>/dev/null || true' EXIT
  sleep 3
  curl -fsS --max-time 5 http://127.0.0.1:8830/health; echo
  curl -sS --max-time 5 -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8830/v1/application-shell/status
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  trap - EXIT
  tail -20 /tmp/scec-v1010.log
fi
```
Expected health version `10.1.0`, status HTTP 503 (default disabled). The temporary process stops. Do not enable live operations.
