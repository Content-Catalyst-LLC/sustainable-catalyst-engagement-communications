#!/usr/bin/env bash
# MEDIA-09.1 source preflight. No database, web, HubSpot or email calls.
set -euo pipefail
cd "$(dirname "$0")/../.."
echo "=== MEDIA-09.1 exact source head ==="
git rev-parse HEAD
echo "=== STATIC SYNTAX ==="
python -m compileall -q backend/app/media09_press.py backend/app/persistence/media09.py backend/alembic/versions/media09_1_001_press_inquiries.py backend/tests/test_media09_press.py
echo "=== FOCUSED TESTS ==="
PYTHONPATH=backend python -m pytest -q backend/tests/test_media09_press.py backend/tests/test_media09_governance.py backend/tests/test_intake_v910.py
echo "=== IMPLEMENTATION GATES ==="
echo "Source checks passed. PostgreSQL migration, actual identity, backups, public WordPress and production acceptance remain NOT VERIFIED."
