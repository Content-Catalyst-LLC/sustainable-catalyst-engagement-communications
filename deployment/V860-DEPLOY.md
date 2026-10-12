# v8.6.0 — Mac + Contabo non-writing deployment

## Mac

Download the complete ZIP, then:

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v8.6.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
git status --short
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v8.6.0/ ./
cd backend
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
git diff --check
git status --short
git add backend docs deployment README.md CHANGELOG.md RELEASE-MANIFEST.json RELEASE-MANIFEST-v8.6.0.md
git diff --cached --stat
git commit -m "Build v8.6.0 identity authorization and privacy"
git push origin main
```

Expected: 71 tests pass. Verify the commit includes `app/identity.py`, `tests/test_identity_v860.py` and v8.6 release docs.

## Contabo — source installation and tests

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v860
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v860/repository
cd /opt/scec-v860/repository/backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q -o addopts=""
git -C .. log -1 --oneline
```

No Alembic upgrade required. Database revision stays `850_001`, table count stays 18. Preserve old services; no need to rerun v8.5 migration. **Never paste signing secrets or tokens into chat or logs.**

## Configure separate bound-mode service without writes

Using the existing root-owned `/etc/sustainable-catalyst/engagement/v800.env`, provision a separate root-owned `/etc/sustainable-catalyst/engagement/v860.env` containing a new randomly generated signing key and `SCEC_IDENTITY_MODE=bound`. Keep `SCEC_PERSISTENCE_ENABLED=0`. You can provision it with:

```bash
sudo install -m 0600 -o root -g root /dev/null /etc/sustainable-catalyst/engagement/v860.env
KEY=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')
printf 'SCEC_IDENTITY_MODE=bound\nSCEC_IDENTITY_SIGNING_KEY=%s\n' "$KEY" | sudo tee /etc/sustainable-catalyst/engagement/v860.env >/dev/null
unset KEY
sudo chmod 600 /etc/sustainable-catalyst/engagement/v860.env
```

Create service:

```bash
sudo tee /etc/systemd/system/scec-v860.service >/dev/null <<'EOF'
[Unit]
Description=Sustainable Catalyst Engagement & Communications v8.6.0
After=network.target postgresql.service
[Service]
Type=simple
User=catalystadmin
WorkingDirectory=/opt/scec-v860/repository/backend
EnvironmentFile=/etc/sustainable-catalyst/engagement/v800.env
EnvironmentFile=/etc/sustainable-catalyst/engagement/v860.env
Environment=PYTHONPATH=.
Environment=SCEC_PERSISTENCE_ENABLED=0
ExecStart=/opt/scec-v860/repository/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8816
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now scec-v860
systemctl is-active scec-v860
curl -fsS http://127.0.0.1:8816/health; echo
curl -sS -o /dev/null -w 'Unauthenticated HTTP %{http_code}\n' http://127.0.0.1:8816/v1/contracts/canonical
sudo -u postgres psql -d scec_engagement_v820 -Atc 'SELECT version_num FROM alembic_version;'
```

Expect active, health version 8.6.0, unauthenticated 401, database `850_001`. Complete separately controlled issuer, subject identity verification, authorization integration and dedicated PostgreSQL tests before enabling writes. Do not expose 8816 publicly; do not change WordPress.
