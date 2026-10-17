# v10.6.0 Mac / Contabo validation — STAGING ONLY

Precondition: clean git tree at v10.5.0, no production configuration changes. Extract ZIP into dedicated directory; copy contents into existing repo (do not copy `.git`/`.venv`).

Mac:
```bash
cd ~/Downloads
mkdir -p scec-v1060-release
unzip -oq sustainable-catalyst-engagement-communications-v10.6.0.zip -d scec-v1060-release
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/scec-v1060-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/privacy_consent_retention_v1060.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.6.0.md RELEASE-CHECKSUMS-v10.6.0.json deployment/V1060-DEPLOY.md
git diff --cached --stat
git commit -m "Build v10.6.0 privacy consent and retention readiness"
git push origin main
```

Contabo after push, via `ssh catalystadmin@94.72.113.77`:
```bash
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1060
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1060/repository
cd /opt/scec-v1060/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8835 )'
```

If port 8835 is available, in Contabo SSH session A:
```bash
cd /opt/scec-v1060/repository/backend
source .venv/bin/activate
SCEC_PRIVACY_RETENTION_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8835
```
In a second SSH session B **on Contabo**:
```bash
curl -fsS http://127.0.0.1:8835/health && echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8835/v1/privacy-consent-retention/status
```
Expected health JSON reports version `10.6.0`; safety endpoint returns 503 with flag disabled (or 401 if authorization precedes gate). Press Ctrl+C in session A and verify `sudo ss -ltnp '( sport = :8835 )'` has no LISTEN row.

All seven production acceptance gates remain open. DO NOT enable staged feature flags, approve draft retention periods, apply DB migrations or expose this service publicly. No WordPress changes, DNS/Caddy/Docker edits or production restarts.
