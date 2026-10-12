# Release v8.9.0 — Production Consolidation & Certification

This release is a **non-mutating preflight and certification gate**. It does NOT certify public deployment or permit production customer data.

- Backend at Contabo: v8.6.0 on loopback port 8816.
- Standalone frontend: v8.7.0 nginx/Docker on loopback port 8097.
- Installed WordPress bridge: v8.8.2 (Contact, Feedback, Feature Suggestions, Channel, Support remain separate).
- PostgreSQL: unchanged at Alembic `850_001`.
- Customer-data persistence: remains disabled.
- No new WordPress ZIP or VPS service is needed for v8.9.0.
- No assumptions about a live public domain or valid TLS certificate.

**Certification is incomplete** until public HTTPS, real browser access, human session broker, CSRF/session revocation, organization-specific role isolation, privacy policy, and staged write acceptance are independently validated.
