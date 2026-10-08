# v8.2.0 Persistence & Migration Foundation

- **Never** set `SCEC_DATABASE_URL` to an existing WordPress, Library, Workspace, or Support database. Provision a **new dedicated** database with a separate limited-role credential.
- Migration creates 12 canonical tables plus `import_batches`, using JSONB payloads with relational canonical identifiers, tenant-bound organization foreign keys and unique source-qualified legacy keys.
- UUID, timestamps and JSONB are persisted without automatically processing or relocating user data.
- Canonical JSONB is not a substitute for authorization. Future write APIs must validate Pydantic models, enforce tenant identity from authenticated context and authorize every read/write.
- The rehearsal utility is read-only, requires a JSON array with `{ "model": "contacts", "record": { ... } }` entries, and returns structured validation errors, counts and zero writes.
- **No legacy migration implemented.** No live data is copied. No background jobs or exposed database endpoints.
- Downgrade intentionally blocked. To reverse a rehearsal, drop only a verified disposable test database. For a real dedicated DB, restore a pre-migration snapshot after change approval.
- PostgreSQL migration is additive to a *dedicated empty database*, not tested against any shared production schema. Require `alembic current` and a backup before upgrades.
