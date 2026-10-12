## 9.2.0 — Feature Suggestions & Community Intelligence
- Authenticated, tenant-bound, read-only feature request classification, priority heuristics, exact within-batch duplicate flags and aggregation previews.
- Writes explicitly rejected; no WordPress, database, or public proxy changes.

## 8.9.0 — Production Consolidation & Certification Preflight
- Introduce read-only source and Contabo preflight checks with JSON report output.
- Preserve deployed backend 8.6.0, web 8.7.0 and WordPress bridge 8.8.2; no new database migration.
- Explicitly mark public HTTPS, human login, tenant isolation, privacy and live writes as uncertified.
- Production writes remain disabled.

## 8.8.2
- Added the existing Feature Suggestions WordPress page as a separate navigation card.

## 8.8.0 — WordPress Compatibility Bridge
- Added WordPress public bridge, settings, scoped styles and standalone launch shortcode. No backend or frontend runtime change.

## 8.7.0 — Standalone Web Application Foundation
- Built responsive independent UI shell covering overview, contacts, engagement, product support, advisory, activity, and access/privacy.
- Refused to misrepresent synthetic records as production; all live data views unconnected and writes disabled.
- Added loopback-only nginx Docker deployment with CSP and security headers.
- Updated backend release health and added frontend/static security regression tests.
- No database migration, no Caddy rewrite, no modifications to v8.6.0 service.

## v8.6.0 — Identity, Authorization & Privacy
- Opt-in signed service-principal verification, tenant-bound roles, approval actor anti-spoofing and privacy-conscious denial telemetry.
- No Alembic migration; writes default disabled.
- Bound mode remains service identity, not independent user identity or complete privacy program.

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

## 9.0.0 — Human authentication and staged session authorization
OIDC PKCE browser sign-in boundary (disabled by default); stateful revocable sessions, CSRF controls, server-side memberships; no production data writes or WordPress changes.
