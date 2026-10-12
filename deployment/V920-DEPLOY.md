# v9.2.0 staging deployment

On Mac: unzip the full ZIP, rsync the extracted folder into the existing clean Git worktree (exclude .git/.venv/__pycache__), run `cd backend && source .venv/bin/activate && python -m pip install -r requirements-dev.txt && PYTHONPATH=. python -m pytest -q -o addopts=""`, run `python certification/certify.py` from repository root, then commit and push.

On Contabo: stage a new clone under `/opt/scec-v920/repository`, create backend virtualenv, install requirements, run tests. Launch temporary localhost `8821` with `SCEC_COMMUNITY_STAGING_ENABLED=0 SCEC_HUMAN_AUTH_ENABLED=0 SCEC_INTAKE_STAGING_ENABLED=0 SCEC_PERSISTENCE_ENABLED=0`, verify GET `/health` is 9.2.0 and GET `/v1/community-intelligence/status` is 503. Shut down the temporary process.

No Caddy changes, WordPress installation or migrations. Leave existing production services running.
