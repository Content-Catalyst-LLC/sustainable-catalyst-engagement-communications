# v10.2.0 Mac and Contabo staging deployment

This release archive is **flat at ZIP root**. Always extract to a dedicated directory. Never change existing Caddy, WordPress, Docker, services, DNS, migrations or public ports.

## Mac

```bash
cd ~/Downloads
mkdir -p scec-v1020-release
unzip -oq sustainable-catalyst-engagement-communications-v10.2.0.zip -d scec-v1020-release
test -f scec-v1020-release/backend/app/identity_certification_v1020.py || exit 1
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/scec-v1020-release/ ./
cd backend && source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd .. && python certification/certify.py
git diff --check
git add backend/app/main.py backend/app/identity_certification_v1020.py backend/app/session_security_checks_v1020.py backend/tests certification/certify.py README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v10.2.0.md RELEASE-CHECKSUMS-v10.2.0.json deployment/V1020-DEPLOY.md
git diff --cached --stat
git commit -m 'Build v10.2.0 production identity session certification staging'
git push origin main
```

## Contabo

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1020
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1020/repository
cd /opt/scec-v1020/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd .. && python3 certification/certify.py
```

## Loopback smoke test, on Contabo only

```bash
cd /opt/scec-v1020/repository/backend
source .venv/bin/activate
ss -ltnp '( sport = :8831 )' # stop if any existing listener; do not kill unknown service
SCEC_IDENTITY_CERT_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8831
```

In a **second SSH session to Contabo**:

```bash
curl -fsS http://127.0.0.1:8831/health
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8831/v1/identity-certification/status
```

Expected health: version `10.2.0` and phase `production-identity-session-certification-staging`; disabled assurance status HTTP 503 (service authentication may reject with 401 first if no bearer is supplied). Press Ctrl+C in the first SSH session afterward. No production certification is granted.
