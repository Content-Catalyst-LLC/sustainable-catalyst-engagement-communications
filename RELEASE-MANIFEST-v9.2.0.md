# v9.2.0 — Feature Suggestions & Community Intelligence

Staging-only authenticated preview/aggregation API; read-only by construction. No database migrations, persistence, external network calls, emails, queues or changes to WordPress.

Routes: `GET /v1/community-intelligence/status`, `POST /v1/community-intelligence/preview`, `POST /v1/community-intelligence/aggregate-preview`, `POST /v1/community-intelligence/commit` (503 always for authorized principals).

Feature flag `SCEC_COMMUNITY_STAGING_ENABLED=0` defaults off. `SCEC_IDENTITY_MODE=bound`, `SCEC_ALLOWED_ORGANIZATION_IDS`, authenticated `contact_editor`/`administrator` service bearer, and matching organization header required. No human cookie authorization.

Classification is transparent rule-based keyword matching. Duplicate detection compares exact normalized fingerprints *only within the supplied batch*, not global community records or semantic similarity. Priority scores are heuristic preview indicators, not decisions. No user-authored text is reflected in responses.

Not a connected WordPress form processor, cross-user aggregator, production recommendation engine, or live ingestion system. v9.0.0 human authentication is not production certified.
