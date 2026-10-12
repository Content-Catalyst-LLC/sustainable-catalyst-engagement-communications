# v9.3.0 deployment

Complete Mac and Contabo instructions are provided alongside the ZIP delivery. No production deploy, WordPress modification, schema change, or migration.

Test: `cd backend && PYTHONPATH=. python -m pytest -q -o addopts=""`.
Preflight: `python certification/certify.py` from repository root.
Start on an unused loopback port 8822 with all staging and persistence switches disabled. Expect health `9.3.0` and status gate `503`. Kill temporary process after verification.
