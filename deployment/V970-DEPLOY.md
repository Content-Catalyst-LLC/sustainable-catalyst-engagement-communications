# Engagement & Communications v9.7.0 — Mac / Contabo staging deployment

Production writes, communications, deletion, consent mutation, and all other new staging services stay disabled. Preserve all five Bluehost WordPress pages. No Caddy changes, system upgrades, database migrations, or service restarts.

## Mac Terminal

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.7.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# STOP if git status showed any files before the pull
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v9.7.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/privacy_governance_v970.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v9.7.0.md RELEASE-CHECKSUMS-v9.7.0.json deployment/V970-DEPLOY.md
git diff --cached --stat
git commit -m "Build v9.7.0 Privacy Retention and Consent Governance"
git push origin main
```

Expected tests: **190 passed**. Certification: `preflight=PASS`, `production_certified=false`, `production_writes_enabled=false`.

## Contabo Terminal — one SSH session

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v970
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v970/repository
cd /opt/scec-v970/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd /opt/scec-v970/repository
python3 certification/certify.py
```

Expected tests: **190 passed**. Do not proceed if clone, tests, or preflight fails.

## Loopback-only smoke test, safe shutdown

```bash
cd /opt/scec-v970/repository/backend
source .venv/bin/activate
if ss -ltn | grep -q ':8826 '; then
  echo 'Port 8826 occupied — stop and investigate; do not kill the existing process.'
else
  SCEC_PRIVACY_STAGING_ENABLED=0 SCEC_ANALYTICS_STAGING_ENABLED=0 SCEC_COMMUNICATIONS_STAGING_ENABLED=0 SCEC_INSTITUTIONAL_STAGING_ENABLED=0 SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 SCEC_COMMUNITY_STAGING_ENABLED=0 SCEC_INTAKE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8826 > /tmp/scec-v970-staging.log 2>&1 &
  pid=$!
  trap 'kill "$pid" 2>/dev/null || true' EXIT
  sleep 3
  echo '=== HEALTH ==='
  curl -fsS --max-time 5 http://127.0.0.1:8826/health
  echo
  echo '=== PRIVACY GATE (expected HTTP 503) ==='
  curl -sS --max-time 5 -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8826/v1/privacy-governance/status
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  trap - EXIT
  tail -20 /tmp/scec-v970-staging.log
fi
```

Expected health JSON includes `"version":"9.7.0"`, `"phase":"privacy-retention-consent-governance-staging"`. Safety gate: HTTP 503. Shutdown log: complete. This validates **staging only** and is not production certification.
