## 8.5.0 — Advisory & Institutional Workflows

- Added proposed engagements, human-gated activation requests, independent reviewer references, advisory transitions, tenant-scoped history and approval metadata.
- Added forward-only migration `850_001` with two additional tables (16 -> 18).
- Retained v8.4 support endpoints and disabled-by-default production persistence.
- No WordPress writes/imports, no automatic approval. Reviewer references are supplied by service clients; full user identity/RBAC deferred to v8.6.

# Changelog

## v8.4.0 — Product Support Python Modernization
- Support case service endpoints; support history and feedback tracking.
- Explicit manual status transition matrix, row-locking, atomic audit writes.
- Alembic `840_001` append-only support history table.
- v8.3.0 persistence transaction repair.
- 52 automated tests passed locally.
- WordPress and older backend deployments remain unchanged.

## v8.3.0 — Contact & Engagement Python Migration
See repository history for previous milestones.
