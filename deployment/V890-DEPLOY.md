# v8.9.0 — Mac, GitHub, Contabo Certification Instructions

## Mac: install and test the consolidated source

1. Download `sustainable-catalyst-engagement-communications-v8.9.0.zip` to `~/Downloads`.
2. Run:

```bash
cd ~/Downloads
unzip -oq sustainable-catalyst-engagement-communications-v8.9.0.zip
cd ~/Projects/sustainable-catalyst-engagement-communications
rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' ~/Downloads/sustainable-catalyst-engagement-communications-v8.9.0/ ./
cd backend
source .venv/bin/activate
PYTHONPATH=. python -m pytest -q -o addopts=""
cd ..
python3 certification/certify.py
node --check frontend/assets/app.js
git diff --check
git status --short
```

3. Review your diff, then commit and push:

```bash
git add -A
git diff --cached --stat
git commit -m "Build v8.9.0 production consolidation certification preflight"
git push origin main
```

## Contabo: non-mutating certification

This step does **not** start a new backend, modify the v8.7 Docker container, change PostgreSQL, or modify the existing WordPress plugin.

```bash
ssh catalystadmin@94.72.113.77
sudo install -d -o catalystadmin -g catalystadmin /opt/scec-v890
# Only if repository does not yet exist:
git clone https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications.git /opt/scec-v890/repository
cd /opt/scec-v890/repository
python3 certification/certify.py --live --json-out ~/scec-v890-certification.json
```

Review `preflight` and individual checks in the report. `production_certified` intentionally stays false. If any check fails, inspect that check before proceeding. Do not enable persistence or public APIs.

## Public HTTPS gate (separate approval)

No public hostname, DNS, TLS certificate, or reverse-proxy configuration is asserted or changed by this package. First choose a hostname, confirm DNS and Caddy/Nginx configuration, and independently validate redirects, browser loads, CSP, cache headers and that **only the static app** is public. No browser-to-backend access or signing key exposure.

## Pending gates

- Browser acceptance on real HTTPS hostname and WordPress launcher URL
- Human authentication with secure HttpOnly server-issued sessions and CSRF protection
- Token/session revocation and expiry
- Adversarial live organization isolation, role scopes, and privacy retention
- Scoped, reversible production-write acceptance (NOT enabled)
