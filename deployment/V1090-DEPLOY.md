# Engagement & Communications v10.9.0 — Isolated staging deployment

**Source preflight does not certify live production acceptance.** All seven live gates remain pending. Never enable production writes, outbound delivery, human login, deletion or federation based on these tests. No WordPress edits, database migrations or production restarts.

## Mac (after downloading ZIP to ~/Downloads)
```bash
cd ~/Downloads
mkdir -p scec-v1090-release
unzip -oq sustainable-catalyst-engagement-communications-v10.9.0.zip -d scec-v1090-release
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# STOP if dirty or pull fails.
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ ~/Downloads/scec-v1090-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
# After review: stage release files, commit and push.
```

## Contabo (after git push, isolated clone)
```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1090
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1090/repository
cd /opt/scec-v1090/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8838 )'
# Start ONLY if port is free:
cd backend
SCEC_ACCEPTANCE_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8838
```
In a second Contabo SSH session:
```bash
curl -fsS http://127.0.0.1:8838/health; echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8838/v1/production-acceptance/status
```
Expected health HTTP 200 (`version=10.9.0`); acceptance status HTTP 503 or 401. Stop test Uvicorn with Ctrl+C, then verify `sudo ss -ltnp '( sport = :8838 )'` has no LISTEN entry.
