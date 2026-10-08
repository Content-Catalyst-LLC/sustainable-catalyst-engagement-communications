# v8.1.0 — Canonical Data and Object Model

This release defines **validation contracts**, not persistence, ingestion or migration execution. It is a non-breaking extension to v8.0.0.

## Namespaces and ownership

- `organizations`, `contacts`, `inquiries`, `advisory_engagements`: contact/intake domain.
- `cases`: support domain.
- `newsletters`: publishing domain.
- `forms`, `surveys`, `submissions`: forms domain; separate metadata from sensitive answer payloads.
- `tests`: tests domain; answer keys referenced rather than exposed in lists.
- `assessments`: assessments domain; human review defaults on.
- `engagement_events`: analytics domain; event subjects referenced by opaque identifiers.

## Identity and legacy migration

Each object receives a UUID. Original IDs stay in `legacy_identity` with explicit source system and object type, never reused as UUIDs. Preserve originals; deduplicate only through reviewed migration rules. `organization_id` is a tenant boundary, not automatic authorization.

## Privacy and governance

Classification is explicit: public, internal, confidential, restricted. Contacts must not be public; submissions must be confidential or restricted. Marketing consent defaults to false and cannot be inferred from a support ticket or contact inquiry. Full access control, data deletion/retention, event governance, field-level encryption and auditable migrations remain later work.

## APIs

Authenticated GET `/v1/contracts/canonical` returns the model names and persistence=none. GET `/v1/contracts/canonical/{name}/schema` returns JSON schema. No new write API is available. Existing v8.0.0 endpoints remain.

## Release constraints

- Database schema, indexes and migration scripts: v8.2.0.
- Actual mapping of legacy entities: v8.3.0 and v8.4.0.
- Production RBAC / shared identity: v8.6.0.
- This release does not retire either legacy system.
