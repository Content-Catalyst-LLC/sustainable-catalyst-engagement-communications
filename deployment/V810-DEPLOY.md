# v8.1.0 deployment (Contabo)

## Mac

Copy this release over your clean Git repository, preserving its `.git` directory, then run tests and push to GitHub. See response instructions.

## VPS (after GitHub push)

Use an isolated `/opt/scec-v810` directory and a new `scec-v810` systemd service on port 8811 for certification. Reuse the **existing** protected `/etc/sustainable-catalyst/engagement/v800.env` token and do not expose ports publicly. Never stop `scec-v800` before v8.1 certification passes. Do not attempt migrations in this release.
