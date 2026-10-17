# v10.8.0 — Mac / Contabo isolated staging

Production use, live telemetry, all writes and outbound traffic are prohibited. All five WordPress pages remain unchanged.

## Mac (after extracting full ZIP in ~/Downloads/scec-v1080-release)

```bash
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
git pull --ff-only origin main
# STOP if dirty or pull fails
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ ~/Downloads/scec-v1080-release/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python certification/certify.py
git diff --check
# See accompanying terminal instructions before commit / push
```

## Contabo (after successful git push)

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1080
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1080/repository
cd /opt/scec-v1080/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
sudo ss -ltnp '( sport = :8837 )'
# ONLY if free:
cd backend
SCEC_RELIABILITY_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0 SCEC_OUTBOUND_ENABLED=0 SCEC_DELETION_ENABLED=0 SCEC_FEDERATION_ENABLED=0 PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8837
```

From another Contabo SSH session:

```bash
curl -fsS http://127.0.0.1:8837/health; echo
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8837/v1/observability-reliability/status
```

Expected backend health 200 version 10.8.0, gated endpoint 503 (or 401). Stop Uvicorn with Ctrl+C; verify `sudo ss -ltnp '( sport = :8837 )'` has no listener. No production restarts, DNS modifications, WordPress changes or database migrations.
