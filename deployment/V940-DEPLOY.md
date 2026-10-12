# v9.4.0 — Mac + Contabo staging deployment

Never modify the five live WordPress pages, production ingress, Caddy, or PostgreSQL for this release. No migrations. These new preview endpoints never commit records. Existing legacy persistence APIs retain their own established opt-in gates.

## Mac

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.4.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v9.4.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/institutional_intelligence_v940.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v9.4.0.md deployment/V940-DEPLOY.md
git diff --cached --stat
git commit -m "Build v9.4.0 Institutional Relationships and Advisory"
git push origin main
```

## Contabo (one SSH session)

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v940
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v940/repository
cd /opt/scec-v940/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
cd backend
if ss -ltn | grep -q ':8823 '; then echo 'PORT 8823 IN USE — STOP'; else
  SCEC_INSTITUTIONAL_STAGING_ENABLED=0 SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0 SCEC_COMMUNITY_STAGING_ENABLED=0 SCEC_INTAKE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8823 > /tmp/scec-v940-staging.log 2>&1 &
  PID=$!
  sleep 3
  curl -fsS http://127.0.0.1:8823/health; echo
  curl -sS -o /dev/null -w 'Institutional gate HTTP %{http_code}\n' http://127.0.0.1:8823/v1/institutional-intelligence/status
  kill "$PID"; wait "$PID" 2>/dev/null || true
  tail -20 /tmp/scec-v940-staging.log
fi
```

Expect 9.4.0 phase institutional-advisory-intelligence-staging, gate HTTP 503, clean shutdown. No service persistence or public route changes. Production certification remains false.
