# v8.7.0 — Standalone Web Application Foundation
- Real deployable static standalone application, no backend credential exposure
- Responsive sidebar and seven navigable workspaces
- Explicitly read-only no-records display; actions disabled
- Standalone nginx container on loopback 8097
- Backend v8.7.0 release health; unchanged API/security model from v8.6.0
- Database Alembic remains at 850_001; no migration
- Security acceptance gate: future BFF + true user auth before live records/writes
