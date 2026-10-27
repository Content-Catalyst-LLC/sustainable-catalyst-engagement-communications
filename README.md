# v12.0.0 — Unified communication object lineage contracts

Default-off synthetic, tenant-bound offline preview. No production activation. See RELEASE-MANIFEST-v12.0.0.md and deployment/V1200-DEPLOY.md.

# v11.9.0 — Synthetic audience aggregates and v11 integration assurance

Default-off synthetic, tenant-bound offline preview. No production activation. See RELEASE-MANIFEST-v11.9.0.md and deployment/V1190-DEPLOY.md.

# v11.8.0 — Read-only embed and distribution API contracts

Default-off synthetic, tenant-bound offline preview. No production activation. See RELEASE-MANIFEST-v11.8.0.md and deployment/V1180-DEPLOY.md.

# v11.7.0 — Partnership and institutional routing previews

Default-off synthetic, tenant-bound offline preview. No production activation. See RELEASE-MANIFEST-v11.7.0.md and deployment/V1170-DEPLOY.md.

# v11.6.0 — Events and webinar previews

Synthetic event metadata, timezone-aware schedules, reviewed speaker attribution, cancellation/update notices and offline ICS preview. No registration, calendar writes, invitations, publication or broadcasting. See RELEASE-MANIFEST-v11.6.0.md and deployment/V1160-DEPLOY.md.

# v11.5.0 — Academic citation and discovery previews

Synthetic metadata exports: BibTeX, RIS, CSL-JSON and schema.org JSON-LD. No DOI invention, identifier lookup, indexing registration or publication. See RELEASE-MANIFEST-v11.5.0.md and deployment/V1150-DEPLOY.md.

# Current release: v11.4.0 — Media Relations & Press Outreach

Synthetic-only media outlet classifications, opaque spokesperson references, source/rights verification and embargo-aware press pitch previews. No real contact data, contact export, sending or public press publication. Default-off SCEC_MEDIA_STAGING_ENABLED, existing bound service/tenant/administrator gates. Source/revision and preview-as-of timestamps form deterministic evidence; embargo clearance and all reviews affect preview only. See deployment/V1140-DEPLOY.md. All seven live gates stay pending; production unchanged.

---

# Current release: v11.3.0 — Newsletter & Research Alerts

Offline synthetic preferences, deterministic tenant-bound segmentation and source/revision fingerprints for reviewed alert composition. Eight topics, four frequency labels and email/in-app preview types; no real subscribers, contacts, persistence, sending, scheduling or public publication. The independent SCEC_ALERTS_STAGING_ENABLED flag defaults to 0. Enabled previews require existing bound service authentication, a matching allowlisted tenant and administrator role. All approvals affect preview eligibility only. Rejected payloads do not echo contact values.

See deployment/V1130-DEPLOY.md and RELEASE-MANIFEST-v11.3.0.md. Five WordPress destinations, frontend and migrations remain unchanged; all seven production gates remain pending. Historical documentation below is not production authorization.

---

# Current release: v10.1.0 — Unified Application Shell & Navigation
Read-only standalone UI; no network calls, persistence or real identity federation. Production certification pending. See `deployment/V1010-DEPLOY.md`.

# v8.8.0 — WordPress Bridge

See `wordpress-bridge/README.md` and `deployment/V880-DEPLOY.md`. No Python, web container, or PostgreSQL changes are required for this release.

# Sustainable Catalyst Engagement & Communications v8.7.0

Standalone web shell + optional versioned FastAPI backend. The UI is **not yet connected to private institutional records**: no user login, no browser credentials, no synthetic live data, and no production writes. Run frontend independently on Contabo at loopback port 8097, keeping v8.6.0 private backend alive on port 8816. Details in `deployment/V870-DEPLOY.md` and `frontend/README.md`.

# Sustainable Catalyst Engagement & Communications — v8.6.0

**Identity, Authorization & Privacy — opt-in bound security foundation.**

Adds `backend/app/identity.py`: HMAC-SHA256 authenticated short-lived service principals with required organization, subject, roles, expiration and audience; per-route RBAC; tenant-header-to-principal binding; advisory/support actor-ref anti-spoofing; pseudonymous authorization-denial logging. Default legacy behavior retained for non-disruptive parallel deployment; `SCEC_IDENTITY_MODE=bound` explicitly activates checks. Tokens are **service-issued assertions**, not verified human login/SSO. No public token issuer exists. Signing key must remain secret and must be distributed by a trusted system; token theft/revocation, key rotation, database RLS and independent external identity verification are not solved by this build.

Schema remains `850_001` (18 tables); **no new migration**. Existing v8.5.0 contact/support/advisory endpoints remain. Writes default disabled. No legacy WordPress changes. See `deployment/V860-DEPLOY.md` and `docs/SECURITY-V860.md`.


## v8.9.0 certification preflight

Run `python3 certification/certify.py` locally, or `python3 certification/certify.py --live` on the Contabo host. See `deployment/V890-DEPLOY.md`. The release does **not** certify production identity/data workflows or enable writes.

## v9.1.0 Contact & Feedback staging intake

Private authenticated preview API (`/v1/intake/status`, `/v1/intake/preview`, `/v1/intake/commit` [always 503]). No WordPress form modification or production data writes. See `deployment/V910-DEPLOY.md`.

## v9.2 staging community intelligence

See `RELEASE-MANIFEST-v9.2.0.md` and `deployment/V920-DEPLOY.md`. This is a non-persistent, gated analysis API, not live WordPress intake.

## v9.3.0 Support intelligence
Authenticated staging-only `/v1/support-intelligence` routes return non-persistent previews; flag `SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=1` is required along with bound identity and tenant allowlist. Writes always rejected. See `deployment/V930-DEPLOY.md`.

## v9.4.0 staging
Read-only institutional and advisory relationship intelligence at `/v1/institutional-intelligence/*`. Disable-by-default flag: `SCEC_INSTITUTIONAL_STAGING_ENABLED=0`; requires bound identity and allowlisted organization if enabled. No production writes, WordPress intake or approval actions.

## v9.5.0 Notifications & Communications
The `/v1/communications-intelligence/*` API provides nonpersistent planning and review only. Enabled for controlled tests with `SCEC_COMMUNICATIONS_STAGING_ENABLED=1`, bound identity and organization allowlist. Outbound delivery and writes remain disabled regardless of flags. No WordPress forms or routes are changed.

## v9.6.0 — Staging Engagement Analytics & Reporting
Tenant-scoped and authenticated `/v1/engagement-analytics/status`, `/report-preview`, `/funnel-preview`, `/export`, `/commit`. Disabled by default. Bound identity, tenant allowlist, and administrator or advisor role required. Request-supplied validated dimensions only (100 events max); no personal data, historical reads, persistence, exports, or outbound delivery.

## v9.7.0 privacy governance staging
`SCEC_PRIVACY_STAGING_ENABLED=0` by default. Bound-identity, allowlisted-tenant metadata previews via `/v1/privacy-governance/*`. No legal decisions, live data ingestion, processing of actual data-subject requests, consent edits, deletion, writes, or outbound messages.

## v9.8.0 federation contract previews
`/v1/federation-intelligence/*` is disabled by default (`SCEC_FEDERATION_STAGING_ENABLED=0`). Enabled previews require bound tenant identity and allowlisted administrator/advisor credentials. No actual cross-platform federation, identity linking, token transfer, persistence, outbound messages, or deletion.

## v9.9.0 — Source assurance
Staging-only `/v1/release-assurance/` status, assessment-preview, reliability-preview and hard-disabled mutation/promotion endpoints. `SCEC_ASSURANCE_STAGING_ENABLED=0` is the default. Source preflight PASS is not production certification.

## Unified platform v10.0.0
Read-only catalog, readiness and consolidation previews under `/v1/unified-platform`. Default disabled: `SCEC_UNIFIED_STAGING_ENABLED=0`. No live login federation or live integration.


## v10.2.0 — Identity & Session Certification (staging-only)

Offline synthetic security fixtures validate cryptographic JWT signature and claims, tenant boundaries, CSRF and expiration/revocation predicates. Gated `/v1/identity-certification/` endpoints disclose only security status and unverified production evidence. No live authentication or persistence is enabled. See `deployment/V1020-DEPLOY.md`.

## v10.3.0 — Tenant isolation and permission enforcement
Offline synthetic policy assertions, nonpersistent staging authorization matrix, deterministic non-certifying report. All existing WordPress pages and migrations preserved; activation, deletion, communications and federation remain disabled. See `deployment/V1030-DEPLOY.md`.

## v10.4.0
Ephemeral in-memory transaction rehearsal with fail-closed service-gated discovery. No production database mutations. See deployment/V1040-DEPLOY.md.

### v10.5.0 WordPress Intake Bridge Certification
The bridge certification engine inspects the bundled, unchanged WordPress launcher source and can produce nonpersistent, non-PII tenant-bound synthetic preview evidence. It makes **no live WordPress requests**, transmits no user submissions and never enables production changes. See `deployment/V1050-DEPLOY.md`.

## v10.6.0
Synthetic privacy/consent/retention readiness only. Draft retention values are not approved policy; no personal data is accepted, stored, exported or deleted by the v10.6 module.

## 10.7.0 staging-only communications delivery foundation
`/v1/delivery-infrastructure/status`, `/contracts`, and `/preview` require opted-in bound service identity; all transport, queue, send, approval, persistence and production promotion endpoints remain blocked. No WordPress changes. See `deployment/V1070-DEPLOY.md`.

### v10.8.0 observability and recovery
Staging-only synthetic reliability assessments are under `/v1/observability-reliability`. They do not collect logs or metrics, send alerts, execute retries, restore backups, store incidents or permit production promotion. See `deployment/V1080-DEPLOY.md`.

### v10.9.0 source-only production acceptance ledger
Review the seven unresolved live gates using `/v1/production-acceptance` under isolated, authenticated staging only. No live gate can be certified in the application. See `deployment/V1090-DEPLOY.md`.

### v11.0.0 research distribution preview foundation
Read-only research manifest contracts for provenance-aware distribution planning. All outlets and actual publication remain disabled. See `deployment/V1100-DEPLOY.md`.

## v11.1.0 RSS, Atom and JSON Feed previews
Staging-only serializer at `/v1/research-feeds/preview`, requiring existing bound service identity and organization allowlisting. No publicly served feeds or live distribution. Seven production acceptance gates remain pending.

## v11.2.0 — Institutional Newsroom
Tenant-bound synthetic newsroom announcement and release-history previews with provenance, editorial states, rights, privacy, source integrity and institutional review. No live publication, distribution, transport, persistence, or authorization. All existing WordPress destinations remain untouched. Seven live production gates remain pending.
