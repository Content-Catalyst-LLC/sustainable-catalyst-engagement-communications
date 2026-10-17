# v11.2.0 isolated staging deployment

## Mac
Unzip repository into a temporary folder; confirm `git status --short` is empty before rsync to `~/Projects/sustainable-catalyst-engagement-communications` (exclude `.git`, `.venv`, `__pycache__`). Run `cd backend && source .venv/bin/activate && PYTHONPATH=. python -m pytest -q -o addopts=""` and `cd .. && python certification/certify.py`. Review git diff then commit/push.

## Contabo (isolated; no production changes)
`sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v1120` then `git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v1120/repository`; create backend venv and install requirements-dev.txt; run same tests and source certification. Verify port 8841 is free. Run with all SCEC staging/production sensitive flags =0 and bind uvicorn to 127.0.0.1:8841. Check GET `/health` 200, GET `/v1/institutional-newsroom/status` 503 with no credentials. Ctrl+C; `sudo ss -ltnp '( sport = :8841 )'` must show no listener. No Caddy, WordPress, Docker, DNS, production DB or service changes.
