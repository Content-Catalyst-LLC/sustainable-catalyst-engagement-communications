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
