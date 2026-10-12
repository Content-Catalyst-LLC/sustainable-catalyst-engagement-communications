# v9.6.0 — Engagement Analytics & Reporting deployment

Scope: request-supplied aggregate previews only. WordPress and persistence schema unchanged. No production writes, notification sends, exports or live data ingestion.

## Mac — installation

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.6.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# Stop if the working tree is not clean.
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ \
  ~/Downloads/sustainable-catalyst-engagement-communications-v9.6.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
# Only continue if tests pass and preflight is PASS.
git diff --check
git add backend/app/main.py backend/app/engagement_analytics_v960.py backend/tests \
  certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json \
  RELEASE-MANIFEST-v9.6.0.md RELEASE-CHECKSUMS-v9.6.0.json deployment/V960-DEPLOY.md
git diff --cached --stat
git commit -m "Build v9.6.0 Engagement Analytics and Reporting"
git push origin main
```

## Contabo — staging only (single SSH session)

From Mac:

```bash
ssh catalystadmin@94.72.113.77
```

On Contabo after GitHub push succeeds:

```bash
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v960
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v960/repository
cd /opt/scec-v960/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
```

Only proceed if 175 tests pass and certification preflight is PASS.

Single-session smoke test: use port 8825 if free; do not modify a running process.

```bash
cd /opt/scec-v960/repository/backend
if ss -ltn | grep -q ':8825 '; then
  echo "Port 8825 occupied — stop without changing it"
else
  SCEC_ANALYTICS_STAGING_ENABLED=0 \
  SCEC_COMMUNICATIONS_STAGING_ENABLED=0 \
  SCEC_INSTITUTIONAL_STAGING_ENABLED=0 \
  SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 \
  SCEC_COMMUNITY_STAGING_ENABLED=0 \
  SCEC_INTAKE_STAGING_ENABLED=0 \
  SCEC_HUMAN_AUTH_ENABLED=0 \
  SCEC_PERSISTENCE_ENABLED=0 \
  SCEC_OUTBOUND_ENABLED=0 \
  PYTHONPATH=. .venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port 8825 \
    > /tmp/scec-v960-staging.log 2>&1 &
  PID=$!
  sleep 3
  echo '=== HEALTH ==='
  curl -fsS --max-time 5 http://127.0.0.1:8825/health; echo
  echo '=== ANALYTICS GATE ==='
  curl -sS --max-time 5 -o /dev/null -w 'HTTP %{http_code}\n' \
    http://127.0.0.1:8825/v1/engagement-analytics/status
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  tail -20 /tmp/scec-v960-staging.log
fi
```

Expected version 9.6.0, phase `engagement-analytics-reporting-staging`, health HTTP 200, analytics gate HTTP 503 and clean shutdown. Do not expose staging through Caddy. Do not modify Bluehost WordPress or run database migrations. No outbound transport should be enabled.
