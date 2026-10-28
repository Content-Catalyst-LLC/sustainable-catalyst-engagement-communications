# Public API paths must not silently serve the frontend shell

The live static server returns HTML 200 for `/v1/contracts/canonical` because its SPA fallback handles all paths. This does not indicate an authenticated API or working public integration.

This interim routing correction reserves `/v1` and `/v1/` and returns JSON 503 with `api_activation_pending`. Root, static assets, healthz and browser hash navigation remain unchanged. No API, human login, persistence or feature is enabled, no token is exposed, and no WordPress link/page is modified. This is a fail-closed readiness correction, not completion of authenticated public routing. Actual backend/session integration must replace it only after recovery, identity, tenant/privacy/security gates and owner approval.

Review and test in an owned isolated container using the existing immutable production frontend image with the candidate nginx configuration mounted read-only. Never run the candidate Compose file against the production container name/port, and do not deploy this patch before the required backup and approval.

Executed isolated evidence is committed at `certification/evidence/issue15-public-api-routing.json`. nginx syntax, original root HTML hash, healthz, JSON 503 for /v1, /v1/contracts/canonical and /v1/human-auth/login, and inherited CSP all passed against the exact candidate configuration hash. Owned container/network were removed. This does not certify browser SSO or a live API. Backend regression was not repeated for this nginx-only patch.
