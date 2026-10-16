## 10.1.0 — Unified Application Shell & Navigation
- Grouped responsive application navigation, accessible filter and route breadcrumbs.
- Unified static overview corrected: no obsolete live backend indicator.
- Service-authenticated, staging-only shell catalog and fail-closed mutation routes.
- No changes to WordPress, migrations, or operational safety defaults.

## v10.0.0 — Unified Engagement Platform
- Unified catalog and readiness reporting across prior v9 modules; all operational transitions blocked.
- Extended static frontend navigation without live-data access.
- No WordPress or migration edits.

## v9.9.0 — Security, Reliability & Certification
- Added tenant-scoped, human-review-only assurance and reliability report previews, forbidden-feature flag detection, reproducible hashes and fail-closed promotion routes.
- Preserved WordPress pages and bridge, database schema and migrations, and disabled all production actions.

## v9.8.0 — Cross-Platform Integration & Identity Federation
- Added tenant-bound, non-persistent application handoff and compatibility contract previews.
- Explicitly denies token exchanges, identity links, handoff commits, outbound messaging, deletion, and persistence.
- WordPress bridge and database contracts unchanged.

## v9.7.0 — Privacy, Retention & Consent Governance
- Read-only policy metadata review, consent status assessment, retention review flags, and rights-request previews.
- Deletion, consent mutation, persistence, and external communications explicitly disabled.
- Existing five WordPress links and database migrations preserved.

## v9.6.0 — Engagement Analytics & Reporting
- Added scoped, deterministic, non-persistent aggregate reporting and stage distribution previews.
- Denied export and commit unconditionally, independent of persistence/outbound flags.
- Kept WordPress bridge and database migration files unchanged.

## 9.5.0 — Notifications & Communications
- Added deterministic consent-aware template/channel planning, audit summaries, and mandatory human review.
- Send and commit routes always deny. No external transports, persistence, migrations, or WordPress changes.

## v9.4.0 — Institutional Relationships & Advisory
- Added authenticated, non-persistent relationship classification, lifecycle guidance, portfolio summaries, risk review flags and fail-closed commit route.
- Preserved WordPress bridge and all existing database/schema contracts.

## v9.3.0 — Support case intelligence staging
- Non-persistent support classification, severity, transition guidance and summaries; default-disabled and no WordPress changes.

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
