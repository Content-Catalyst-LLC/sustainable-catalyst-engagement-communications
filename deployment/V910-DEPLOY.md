# v9.1.0 — Controlled staging deployment

## Mac terminal

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v9.1.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short # Must be clean before copying
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v9.1.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
git diff --check
git add backend/app/main.py backend/app/intake_v910.py backend/tests certification/certify.py README.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v9.1.0.md deployment/V910-DEPLOY.md
# Inspect the diff before committing
git diff --cached --stat
git commit -m "Build Engagement and Communications v9.1.0 staged intake"
git push origin main
```

## Contabo terminal

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v910
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v910/repository
cd /opt/scec-v910/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
SCEC_INTAKE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8820
```

In another VPS session:

```bash
curl -fsS http://127.0.0.1:8820/health
curl -sS -o /dev/null -w 'Intake gate HTTP %{http_code}\n' http://127.0.0.1:8820/v1/intake/status
```

The health version should be 9.1.0, intake gate HTTP 503 when default/legacy configuration is used. Stop the temporary uvicorn with Ctrl+C. No Caddy, WordPress, PostgreSQL, or systemd modifications are required. To enable *staging preview*, first configure signed bound principals and allowed organizations; never put service keys in browser scripts or WordPress public code. Do not enable `SCEC_PERSISTENCE_ENABLED` for production.
