# v8.4.0 Release Manifest

**Scope:** Product Support Python Modernization; repository bundle; based on v8.3.0.

**Migration:** `840_001`, down_revision `830_001`, creates `support_history`; previous tables left intact. Total expected application + Alembic tables after migration: **16** (15 prior + 1).

**API:** POST /v1/support/cases; GET /v1/support/cases; GET /v1/support/cases/{case_id}; POST /v1/support/cases/{case_id}/transitions; POST /v1/support/cases/{case_id}/feedback; GET /v1/support/cases/{case_id}/history.

**Controls:** shared service bearer-token access (ensure `SCEC_AUTH_MODE=token`), explicit tenant allowlist, PostgreSQL opt-in, mandatory existing organization, requester tenant validation, row lock on mutations, append-only case event history. Actor references are supplied by trusted service; not independently identity-attested in v8.4.

**Unsupported:** external WordPress import, public front end, attachment upload, automatic product registry synchronization, agent RBAC, outbound notifications, support SLA execution.

**Certification:** 52 local tests; live migrations, restore rehearsal, auth and cross-tenant integration tests remain deployment gates.
