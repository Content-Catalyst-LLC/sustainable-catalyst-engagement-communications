# v10.2.0 — Production Identity & Session Certification Foundation

Staging-only security assessment and synthetic-fixture regression checks for asymmetric OIDC JWT verification, issuer/audience, expiry, not-before, tenant membership, role isolation, CSRF origin, and session revocation semantics.

The legacy v9.0 OIDC code and the WordPress bridge are not changed. No live identities, production writes, real deletions, outbound messaging, or token federation are activated. Live production certification remains **false** with seven acceptance gates outstanding.

API: `GET /v1/identity-certification/status`, `GET /requirements` (both service-authenticated, bound-tenant-scoped, staging flag required); all mutation routes return 503. Default staging gate is off.
