# v11.0.0 — isolated staging only

## Mac
```bash
cd ~/Downloads
mkdir -p scec-v1100-release
unzip -oq sustainable-catalyst-engagement-communications-v11.0.0.zip -d scec-v1100-release
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# Stop if tree is dirty or pull fails. Copy from archive only after review.
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ ~/Downloads/scec-v1100-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
# After successful verification: git add relevant files; git commit; git push origin main
```

## Contabo (after pushing main)
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1100
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1100/repository
cd /opt/scec-v1100/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8839 )'
# Only if free:
cd backend
SCEC_DISTRIBUTION_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8839
```
In second Contabo SSH session:
```bash
curl -fsS http://127.0.0.1:8839/health; echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8839/v1/research-distribution/status
```
Expected health version 11.0.0, gated status 503 (or auth 401). Stop Uvicorn with Ctrl+C and confirm no listener on 8839. No production activation or live acceptance certification occurs.
