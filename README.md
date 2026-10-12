# Sustainable Catalyst Engagement & Communications — v8.5.0

**Product Support Python Modernization**. Builds upon the v8.3.0 tenant-scoped contact and inquiry persistence foundation.

- New service-only support case API for creation, tenant-filtered retrieval/listing, validated triage/status transitions, feedback notes and immutable support history.
- New Alembic `840_001` support history table. Requires `830_001` to be present; do not run v8.2 bootstrap migration again.
- Atomic case creation and audit; controlled status transitions, requester-tenant validation, and explicit product-key capture.
- Fixes v8.3.0 `put_record` indentation/transaction regression that could prevent contact and inquiry persistence.
- Does not migrate legacy WordPress support records, dispatch messages, send mail, trigger automated triage, or enable public submissions.
- Persistent endpoints remain OFF unless `SCEC_PERSISTENCE_ENABLED=1` and PostgreSQL/tenant configuration provided. **Before enabling**, verify service-token security, tenant isolation, and app role privileges.

See `deployment/V840-DEPLOY.md` for exact Mac/Contabo commands. For a non-writing health-only deployment keep persistence off.

Advisory workflows: see deployment/V850-DEPLOY.md.
