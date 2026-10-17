# v10.4.0 Mac and Contabo staging deployment

The ZIP contains repository files at its root; extract into a dedicated directory.

## Mac
```bash
cd ~/Downloads
mkdir -p scec-v1040-release
unzip -oq sustainable-catalyst-engagement-communications-v10.4.0.zip -d scec-v1040-release
test -f scec-v1040-release/backend/app/transaction_foundation_v1040.py
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# ONLY IF working tree is clean:
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/scec-v1040-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/transaction_foundation_v1040.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.4.0.md RELEASE-CHECKSUMS-v10.4.0.json deployment/V1040-DEPLOY.md
git diff --cached --stat
git commit -m "Build v10.4.0 Secure Persistence and Transaction Foundation"
git push origin main
```

## Contabo (only after successful Mac push)
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1040
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1040/repository
cd /opt/scec-v1040/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8833 )'
```

If port 8833 is free, launch temporary server in first SSH session:
```bash
cd /opt/scec-v1040/repository/backend
source .venv/bin/activate
SCEC_TRANSACTION_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8833
```

In a **second SSH session on Contabo**, verify:
```bash
curl -fsS http://127.0.0.1:8833/health; echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8833/v1/transaction-foundation/status
```
Expected health version 10.4.0, safety endpoint HTTP 503 (or 401 if service authentication runs first). Return to first SSH session and press Ctrl+C. Never change Caddy, WordPress, DNS or production services. No schema migrations are needed.
