# Sustainable Catalyst Engagement & Communications — v8.6.0

**Identity, Authorization & Privacy — opt-in bound security foundation.**

Adds `backend/app/identity.py`: HMAC-SHA256 authenticated short-lived service principals with required organization, subject, roles, expiration and audience; per-route RBAC; tenant-header-to-principal binding; advisory/support actor-ref anti-spoofing; pseudonymous authorization-denial logging. Default legacy behavior retained for non-disruptive parallel deployment; `SCEC_IDENTITY_MODE=bound` explicitly activates checks. Tokens are **service-issued assertions**, not verified human login/SSO. No public token issuer exists. Signing key must remain secret and must be distributed by a trusted system; token theft/revocation, key rotation, database RLS and independent external identity verification are not solved by this build.

Schema remains `850_001` (18 tables); **no new migration**. Existing v8.5.0 contact/support/advisory endpoints remain. Writes default disabled. No legacy WordPress changes. See `deployment/V860-DEPLOY.md` and `docs/SECURITY-V860.md`.
