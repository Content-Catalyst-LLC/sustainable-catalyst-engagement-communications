# v9.1.0 — Contact & Feedback Intake Integration (Staging Preparation)

- Added `backend/app/intake_v910.py` with tenant-scoped, service-principal-authenticated validation and preview for Contact and Feedback records.
- Requires `SCEC_INTAKE_STAGING_ENABLED=1` AND `SCEC_IDENTITY_MODE=bound`, allowlisted organization and `contact_editor` or `administrator` role.
- Does not invoke WordPress forms, store submissions, connect to the database, queue jobs, send email or call external integrations. A separate production release and real IdP acceptance are required for actual processing.
- Commit endpoint always returns HTTP 503, including when `SCEC_PERSISTENCE_ENABLED=1`.
- Existing WordPress plugin and five public pages unchanged. No migrations, no service/proxy changes.
- Known limitation: this is a staging intake *contract bridge*, not a deployed WordPress event adapter. It does not affect the existing form delivery mechanisms.
