# v9.8.0 — Mac and Contabo staging instructions

**Safety:** Five Bluehost WordPress pages and the WP bridge stay unchanged. No DB migrations, Caddy modification, outbound messages, deletion, actual federation, identity linking or writes. Production certification pending.

## Mac Terminal

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.8.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
# STOP if not clean
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v9.8.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/federation_intelligence_v980.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v9.8.0.md RELEASE-CHECKSUMS-v9.8.0.json deployment/V980-DEPLOY.md
git diff --cached --stat
git commit -m "Build v9.8.0 Cross Platform Identity Federation Previews"
git push origin main
```

Expected: 205 tests passed. Preflight PASS, certified false, writes false. Stop if push fails.

## Contabo, single SSH session

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v980
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v980/repository
cd /opt/scec-v980/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd /opt/scec-v980/repository
python3 certification/certify.py
```

Stop if tests or preflight fail. Expected: 205 passed.

## Localhost smoke, single terminal

```bash
cd /opt/scec-v980/repository/backend
source .venv/bin/activate
if ss -ltn | grep -q ':8827 '; then
  echo 'Port 8827 occupied. Stop and investigate.'
else
  SCEC_FEDERATION_STAGING_ENABLED=0 SCEC_FEDERATION_ENABLED=0 SCEC_PRIVACY_STAGING_ENABLED=0 SCEC_ANALYTICS_STAGING_ENABLED=0 SCEC_COMMUNICATIONS_STAGING_ENABLED=0 SCEC_INSTITUTIONAL_STAGING_ENABLED=0 SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 SCEC_COMMUNITY_STAGING_ENABLED=0 SCEC_INTAKE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8827 > /tmp/scec-v980-staging.log 2>&1 &
  pid=$!
  trap 'kill "$pid" 2>/dev/null || true' EXIT
  sleep 3
  echo '=== HEALTH (expected v9.8.0) ==='
  curl -fsS --max-time 5 http://127.0.0.1:8827/health
  echo
  echo '=== FEDERATION GATE (expected HTTP 503) ==='
  curl -sS --max-time 5 -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8827/v1/federation-intelligence/status
  kill "$pid" 2>/dev/null || true
  wait "$pid" 2>/dev/null || true
  trap - EXIT
  tail -20 /tmp/scec-v980-staging.log
fi
```

Expected health `version: 9.8.0`, `phase: cross-platform-identity-federation-staging`; status HTTP 503; clean shutdown. Never expose port publicly or restart unrelated services.
