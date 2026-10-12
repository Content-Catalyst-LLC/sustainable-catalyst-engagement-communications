# v8.4.0 deployment — macOS and Contabo

**Prerequisites**: v8.3.0 live DB `scec_engagement_v820` reports revision `830_001`; service `scec-v830` healthy; clean intended Git repository on Mac. Do not work from an accidental Git root in `~/Downloads`.

## macOS: apply release

```bash
mkdir -p ~/Projects
cd ~/Downloads
unzip -q sustainable-catalyst-engagement-communications-v8.4.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git rev-parse --show-toplevel
git status --short
# Only if repo is correct and no unexpected changes:
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
 ~/Downloads/sustainable-catalyst-engagement-communications-v8.4.0/ ./
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q -o addopts=''
cd ..
git diff --check
git add backend deployment README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v8.4.0.md
git commit -m 'Build v8.4.0 Product Support Python Modernization'
git push origin main
```

Expected local tests: **52 passed**. Confirm remote and commit before installing on VPS.

## Contabo: install parallel service (non-writing)

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v840
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v840/repository
cd /opt/scec-v840/repository/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q -o addopts=''
PYTHONPATH=. alembic -c alembic.ini heads
# Expect 840_001 (head); current will need a private connection URL
```

## DB: backup and tested restore **before** migration

```bash
mkdir -p ~/scec-backups/v840
chmod 700 ~/scec-backups/v840
sudo -u postgres pg_dump -Fc -d scec_engagement_v820 > ~/scec-backups/v840/pre-migration.dump
chmod 600 ~/scec-backups/v840/pre-migration.dump
pg_restore --list ~/scec-backups/v840/pre-migration.dump >/dev/null
sudo -u postgres createdb -O scec_engagement_migrator scec_v840_pre_restorecheck
sudo -u postgres pg_restore --exit-on-error --no-owner --role=scec_engagement_migrator \
 -d scec_v840_pre_restorecheck < ~/scec-backups/v840/pre-migration.dump
sudo -u postgres psql -d scec_v840_pre_restorecheck -Atc 'SELECT version_num FROM alembic_version;'
# Expect 830_001. If restorecheck exists, choose another UNIQUE scratch name; do not overwrite.
```

Configure `SCEC_DATABASE_URL` for *this shell only* with migration role password, using the safe password encoding procedure used for v8.3.0. Do not print or paste passwords or URL into logs. Verify the connection refers to dedicated database `scec_engagement_v820`.

```bash
cd /opt/scec-v840/repository/backend
source .venv/bin/activate
PYTHONPATH=. alembic -c alembic.ini current   # 830_001
PYTHONPATH=. alembic -c alembic.ini heads     # 840_001
# Only once backup restore and connection are verified:
PYTHONPATH=. alembic -c alembic.ini upgrade head
PYTHONPATH=. alembic -c alembic.ini current   # 840_001
sudo -u postgres psql -d scec_engagement_v820 -Atc 'SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';'  # 16
```

Create a non-writing service at `127.0.0.1:8814` after checking protected `v800.env` has **SCEC_AUTH_MODE=token** and a strong service token. Do **not** disclose the file contents. A systemd `EnvironmentFile` alone will not supply the database URL unless explicitly configured there.

```bash
sudo tee /etc/systemd/system/scec-v840.service >/dev/null <<'EOF'
[Unit]
Description=Sustainable Catalyst Engagement & Communications v8.4.0
After=network.target postgresql.service
[Service]
Type=simple
User=catalystadmin
WorkingDirectory=/opt/scec-v840/repository/backend
EnvironmentFile=/etc/sustainable-catalyst/engagement/v800.env
Environment=PYTHONPATH=.
Environment=SCEC_PERSISTENCE_ENABLED=0
Environment=SCEC_AUTH_MODE=token
ExecStart=/opt/scec-v840/repository/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8814
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now scec-v840
systemctl is-active scec-v830 scec-v840
curl -fsS http://127.0.0.1:8814/health
curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8814/v1/support/cases
# Expect HTTP 401 without authorization
```

## Post-migration backup and separate restoration

```bash
sudo -u postgres pg_dump -Fc -d scec_engagement_v820 > ~/scec-backups/v840/post-migration.dump
chmod 600 ~/scec-backups/v840/post-migration.dump
sudo -u postgres createdb -O scec_engagement_migrator scec_v840_post_restorecheck
sudo -u postgres pg_restore --exit-on-error --no-owner --role=scec_engagement_migrator \
 -d scec_v840_post_restorecheck < ~/scec-backups/v840/post-migration.dump
sudo -u postgres psql -d scec_v840_post_restorecheck -Atc 'SELECT version_num FROM alembic_version;' # 840_001
sudo -u postgres psql -d scec_v840_post_restorecheck -Atc 'SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';' # 16
```

**Final certification gate**: exercise authenticated create/transition/feedback/history with dedicated nonproduction organization, confirm cross-tenant denial, verify audit writes and row transactions, test least-privilege runtime role, and keep `SCEC_PERSISTENCE_ENABLED=0` until approved. No automated legacy import. No VPS reboot.
