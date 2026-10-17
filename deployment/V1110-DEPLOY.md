# v11.1.0 — RSS / Atom / JSON Feed staging certification

All routes are staging-only, disabled by default, require service bearer identity and an allowlisted tenant. Do not publish or install WordPress changes. All seven live acceptance gates remain pending.

## Mac
```bash
cd ~/Downloads
mkdir -p scec-v1110-release
unzip -oq sustainable-catalyst-engagement-communications-v11.1.0.zip -d scec-v1110-release
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# Stop unless clean and fast-forward succeeds.
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ ~/Downloads/scec-v1110-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
# If all pass, review git diff, stage changes and push.
```

## Contabo after pushing main
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1110
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1110/repository
cd /opt/scec-v1110/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8840 )'
# Only if free:
cd backend
SCEC_DISTRIBUTION_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8840
```
From a second Contabo session:
```bash
curl -fsS http://127.0.0.1:8840/health; echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8840/v1/research-feeds/status
```
Expected health `11.1.0`, gate HTTP 503 or 401. Ctrl+C in original SSH session, confirm no listener `sudo ss -ltnp '( sport = :8840 )'`.
