# v9.9.0 — Security, Reliability & Certification: staged deployment

**Never run these commands against WordPress, live SCEC services, or Site Intelligence.** No production changes or migrations. Treat source `preflight=PASS` as source readiness only; real authentication, privacy, HTTPS, tenant isolation and production acceptance remain pending.

## Mac Terminal (not Contabo)

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.9.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# Stop if local status was nonempty, or pull failed.
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v9.9.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/release_assurance_v990.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v9.9.0.md RELEASE-CHECKSUMS-v9.9.0.json deployment/V990-DEPLOY.md
git diff --cached --stat
git commit -m 'Build v9.9.0 Security Reliability and Certification'
git push origin main
```

Expected: 220 passed; certification preflight PASS; production_certified false; production_writes_enabled false. Only proceed after push succeeds.

## Contabo terminal (open on Mac)

```bash
ssh catalystadmin@94.72.113.77
```

On VPS:

```bash
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v990
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v990/repository
cd /opt/scec-v990/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd /opt/scec-v990/repository
python3 certification/certify.py
```

## One-session smoke test (Contabo)

```bash
cd /opt/scec-v990/repository/backend
source .venv/bin/activate
if ss -ltn | grep -q ':8828 '; then
  echo 'Port 8828 in use: do not proceed.'
else
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
  PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8828 > /tmp/scec-v990-staging.log 2>&1 &
  PID=$!
  trap 'kill "$PID" 2>/dev/null || true' EXIT
  sleep 3
  echo '=== HEALTH (expect 200, version 9.9.0) ==='
  curl -fsS --max-time 5 http://127.0.0.1:8828/health
  echo
  echo '=== SAFETY GATE (expect HTTP 503) ==='
  curl -sS --max-time 5 -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8828/v1/release-assurance/status
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  trap - EXIT
  tail -20 /tmp/scec-v990-staging.log
fi
```

Expected health: `{"status":"ok","service":"engagement-communications","version":"9.9.0","phase":"security-reliability-certification-staging"}`. Disabled assurance route should return 503 in token-disabled mode; source and regression suites independently verify the fail-closed actions. No Caddy, Docker, WordPress or DB changes.
