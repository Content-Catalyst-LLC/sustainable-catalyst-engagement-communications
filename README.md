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
