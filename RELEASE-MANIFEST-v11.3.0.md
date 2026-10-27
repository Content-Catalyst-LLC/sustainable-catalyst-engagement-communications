# v11.3.0 — Newsletter & Research Alerts

Regenerated under issue #6 from verified v11.2.0 commit 61543658d111eac2993abc86206dc8a8479dc562. The absent earlier ZIP and its claimed 625 tests are not verification evidence.

Module: backend/app/newsletter_alerts_v1130.py. Default-disabled GET /v1/research-alerts/status and POST /v1/research-alerts/preview require SCEC_ALERTS_STAGING_ENABLED=1, bound service identity, matching allowlisted organization and administrator role. All dangerous feature flags must remain 0. No human login.

Topics: climate-nature, energy-systems, sustainable-development, methods-data, economics-policy, law-governance, health-society, technology-innovation. Authenticated status includes descriptions. Frequency labels: immediate/daily/weekly/monthly, never scheduling. Channel preview types: email/in-app, never transports.

Fixtures require synthetic=true and synthetic:<canonical nonzero UUID> subscriber references. Consent defaults false; preference state defaults opted-out. Opt-out, suppression, missing consent, review-incomplete/denied, topic/frequency/channel mismatches cannot match. No contact fields or recipient export. Rejected HTTP validation returns a generic 422 without submitted values. Text validation is a bounded fixture contract, not a universal PII detector.

Preview hashes include tenant, object/revision, source references, text, review state, normalized preferences and requested frequency/channel; input order does not alter the hash. Even all fixture approvals never grant production acceptance, subscription activation, publication, syndication, sending, scheduled delivery, persistence, fetching, human login, deletion, federation or token exchange. No cron/worker is introduced.

Fifteen protected frontend/WordPress/migration files plus Alembic configuration are unchanged. Inherited feed/newsroom serializers retain their historical module versions. Source preflight must PASS with production_certified=false, production_writes_enabled=false and live_checks={}; seven live gates stay pending. Actual tests and reviewed Git SHA are recorded in external certification evidence to avoid circular source checksums.
