# MEDIA-05 — Local Build and Security Verification

**Release:** MEDIA-05 WordPress v8.8.9 + additive E&C FastAPI staging route
**Status:** Source packaged and locally verified; not production deployed; no end-to-end remote WordPress↔Contabo test.

## Tests

| Test group | Result |
|---|---|
| New FastAPI contract/authentication/tenant/delivery-block tests | **17 passed** (local test-only identity/router mounting shim; production app integration awaits CI/live acceptance) |
| New WordPress guarded bridge unit checks | **27 passed** |
| MEDIA-04 private CPT/unit tests | **16 passed** |
| MEDIA-04 state-transition integration tests | **34 passed** |
| Prior Media page/MEDIA-02/MEDIA-03 synthetic suites | **Passed** |
| PHP lint, JavaScript syntax and Python compilation | **Passed** |
| ZIP integrity, root folder, expected files | **Passed** |

## Security invariants

- A review request is an explicit, nonce-protected administrator POST. No anonymous or public Media shortcode touches the private backend.
- Backend requires explicit staging flag, existing bound signed principal, administrator role, exact organization allowlist and public-source hostname allowlist. Dangerous production flags block the route.
- WordPress pins an approved HTTPS backend origin, disallows ports, credentials, redirects and unsafe destinations, verifies TLS, and never stores or renders the bearer.
- Only approved, unchanged, published WordPress source metadata and SHA-256 fingerprints may be sent. No subscriber data, manuscript bodies, credentials or private contact data.
- Backend never fetches the source and independently verifies neither rights nor WordPress approval; review facts are explicitly labeled as unverified attestations.
- Every publish/send/sync/schedule/commit/activate/subscribe/recipient-export endpoint remains blocked. No backend persistence or migration.

## Packages

| Artifact | Size | SHA-256 |
|---|---:|---|
| WordPress installable ZIP | 46,086 bytes | `1c1a068e9ea487e5443e3a1daa2fdc9d6f6b845aeb4e349d8f974024d813e4e0` |
| Backend source candidate ZIP | 6,781 bytes | `a4cac5c6ed35c9aa38f8680ddde552ba50cc9fe00d296a29244286921a520487` |

## Outstanding live acceptance

- GitHub Actions against the complete backend application and existing dependencies (local FastAPI suite used a faithful gate shim because this runtime cannot clone the full repository).
- WordPress v8.8.9 install/upgrade and logged-out public Media regression on Bluehost.
- Real administrator-controlled signed token lifecycle; private API hostname, TLS, DNS and tenant isolation checks on Contabo.
- End-to-end staging handshake, receipt review, logs confirming no external posting, and rollback/backups.
- Explicit security and deployment approval before enabling the bridge in production.