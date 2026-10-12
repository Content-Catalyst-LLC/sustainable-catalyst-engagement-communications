# SCEC v8.5.0 — Advisory & Institutional Workflows deployment

Status: packaged/tested locally; production migration, backups, live SQL integration tests, and rollout must be performed by operator.

## Mac — stage and push

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v8.5.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
test "$(git rev-parse --show-toplevel)" = "$(pwd -P)" || { echo 'STOP: wrong Git root'; exit 1; }
git status --short
rsync -av --exclude=.git --exclude=.venv --exclude=__pycache__ ~/Downloads/sustainable-catalyst-engagement-communications-v8.5.0/ ./
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
cd ..
git diff --check
git status --short
git add -A
git commit -m 'Build v8.5.0 Advisory and Institutional Workflows'
git push origin main
```

Do not run `git add -A` unless the `git rev-parse` root check succeeds and you have inspected `git status`. Never run it from ~/Downloads.

## Contabo install, non-writing service

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v850
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v850/repository
cd /opt/scec-v850/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=''
```

### Backup and restore rehearsal BEFORE migration

```bash
install -d -m 700 ~/scec-backups/v850
sudo -u postgres pg_dump -Fc scec_engagement_v820 > ~/scec-backups/v850/pre-migration.dump
chmod 600 ~/scec-backups/v850/pre-migration.dump
pg_restore --list ~/scec-backups/v850/pre-migration.dump >/dev/null
# Use a unique scratch database name; the following must NOT exist yet.
sudo -u postgres createdb -O scec_engagement_migrator scec_v850_restorecheck
sudo -u postgres pg_restore --exit-on-error --no-owner --role=scec_engagement_migrator -d scec_v850_restorecheck < ~/scec-backups/v850/pre-migration.dump
sudo -u postgres psql -d scec_v850_restorecheck -Atc 'SELECT version_num FROM alembic_version;'
# expected 840_001
```

### Upgrade live schema ONLY after restored revision validated

```bash
cd /opt/scec-v850/repository/backend
source .venv/bin/activate
read -rsp 'PostgreSQL migration password: ' DB_PASSWORD; echo
export SCEC_DATABASE_URL="$(DB_PASSWORD="$DB_PASSWORD" python3 - <<'PY'
import os
from urllib.parse import quote
print('postgresql+psycopg://scec_engagement_migrator:'+quote(os.environ['DB_PASSWORD'],safe='')+'@127.0.0.1:5432/scec_engagement_v820')
PY
)"
unset DB_PASSWORD
PYTHONPATH=. alembic -c alembic.ini current
PYTHONPATH=. alembic -c alembic.ini heads
# expect current 840_001 and head 850_001; STOP if different
PYTHONPATH=. alembic -c alembic.ini upgrade head
PYTHONPATH=. alembic -c alembic.ini current
sudo -u postgres psql -d scec_engagement_v820 -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
# expected 850_001, 18 tables
unset SCEC_DATABASE_URL
```

### Service configuration — localhost 8815, writes disabled

```bash
sudo tee /etc/systemd/system/scec-v850.service >/dev/null <<'UNIT'
[Unit]
Description=Sustainable Catalyst Engagement & Communications v8.5.0
After=network.target postgresql.service
[Service]
Type=simple
User=catalystadmin
WorkingDirectory=/opt/scec-v850/repository/backend
EnvironmentFile=/etc/sustainable-catalyst/engagement/v800.env
Environment=PYTHONPATH=.
Environment=SCEC_PERSISTENCE_ENABLED=0
ExecStart=/opt/scec-v850/repository/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8815
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now scec-v850
systemctl is-active scec-v810 scec-v820 scec-v830 scec-v840 scec-v850
curl -fsS http://127.0.0.1:8815/health; echo
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8815/v1/contracts/canonical
# expected five active, version 8.5.0, protected route 401
```

### Post-migration restore rehearsal

```bash
sudo -u postgres pg_dump -Fc scec_engagement_v820 > ~/scec-backups/v850/post-migration.dump
chmod 600 ~/scec-backups/v850/post-migration.dump
pg_restore --list ~/scec-backups/v850/post-migration.dump >/dev/null
# scratch DB must not exist
sudo -u postgres createdb -O scec_engagement_migrator scec_v850_postrestore
sudo -u postgres pg_restore --exit-on-error --no-owner --role=scec_engagement_migrator -d scec_v850_postrestore < ~/scec-backups/v850/post-migration.dump
sudo -u postgres psql -d scec_v850_postrestore -Atc 'SELECT version_num FROM alembic_version;'
sudo -u postgres psql -d scec_v850_postrestore -Atc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
# expect 850_001, 18
```

## Security/certification boundaries

- v8.5.0 service defaults to `SCEC_PERSISTENCE_ENABLED=0`; legacy WordPress processes and prior SCEC services remain running.
- `actor_ref` and `reviewed_by` are *unverified client assertions*. The token protects service access but does not authenticate the reviewer independently. Enforce real user identity, role authorization and approval assignment in v8.6.0 before allowing production writes.
- The approval gate requires a different `actor_ref`, but this is NOT a substitute for RBAC or identity proof.
- New advisory workflow endpoints require the same bearer token and `X-SCEC-Organization-ID` allowlist as other v8 APIs.
- Before production enablement run live SQL integration tests on a separate dedicated test database with isolated tenant IDs, real auth settings, role-scoped credentials and audit assertions.
- No automatic legacy imports, publication, external notification, or WordPress writes.
- Forward-only Alembic; no destructive downgrades. Preserve both backup archives and verify restores.
