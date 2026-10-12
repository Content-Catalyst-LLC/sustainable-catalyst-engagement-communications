# v9.5.0 deployment — Mac and Contabo

## Boundaries
- Existing five WordPress pages and bridge files unchanged.
- Never apply database migrations or change Caddy, Site Intelligence, or production systemd services.
- No SMTP/SMS/webhook/queue transports. `send` and `commit` permanently return HTTP 503.
- Default `SCEC_COMMUNICATIONS_STAGING_ENABLED=0`, `SCEC_PERSISTENCE_ENABLED=0`, `SCEC_OUTBOUND_ENABLED=0`.

## Mac
```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.5.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# STOP if working tree is not clean
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v9.5.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/communications_intelligence_v950.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v9.5.0.md deployment/V950-DEPLOY.md
git diff --cached --stat
git commit -m "Build v9.5.0 Notifications and Communications"
git push origin main
```

## Contabo — single SSH session
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v950
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v950/repository
cd /opt/scec-v950/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
cd backend
if ss -ltn | grep -q ':8824 '; then echo 'PORT OCCUPIED; STOP'; else
 SCEC_COMMUNICATIONS_STAGING_ENABLED=0 SCEC_INSTITUTIONAL_STAGING_ENABLED=0 SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 SCEC_COMMUNITY_STAGING_ENABLED=0 SCEC_INTAKE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8824 > /tmp/scec-v950-staging.log 2>&1 &
 PID=$!
 sleep 3
 curl -fsS http://127.0.0.1:8824/health
 echo
 curl -sS -o /dev/null -w 'COMMUNICATIONS HTTP %{http_code}\n' http://127.0.0.1:8824/v1/communications-intelligence/status
 kill "$PID"; wait "$PID" 2>/dev/null || true
 tail -20 /tmp/scec-v950-staging.log
fi
```
Expected: 160 passed; preflight PASS with `production_certified=false` and writes disabled; health `9.5.0`; communications status `HTTP 503`; clean shutdown. No production deployment.
