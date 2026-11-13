# Current release candidate

See [MEDIA09 release status and runbook](MEDIA09-RELEASE.md) for the 2026-11-13 implementation and actual acceptance. The source-only checkpoint below is historical.

# MEDIA-09.1 — First-Party Press Inquiry and Institutional Contact Management

**Date:** 2026-11-12 (America/Chicago)  
**Status:** SOURCE IMPLEMENTED — synthetic-only, staged candidate. Not deployed, not accepted against PostgreSQL/real identity.  
**Tracking:** [MEDIA #35](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/issues/35)  
**Parent:** MEDIA-09.0 governance foundation. All eleven owner/privacy/provider reviews remain pending.

## Purpose and ownership

This is **first-party** private Press contact and inquiry management. It is not HubSpot. Press/Media keeps the original inquiry, canonical contact, review state and audit history. Workspace/Core retain identity and project permissions; Research/Library retain research outputs; MEDIA-07 retains newsletter authoring and sending rules; MEDIA-08 retains public Press publication approval.

The existing `Contact` and `Inquiry` models and tenant-scoped PostgreSQL tables are authoritative. This increment adds a small `media09_press_inquiries` table for Press-specific message, purpose/category, notice/consent evidence, idempotency digest and review version. **No second contacts database.**

## Features implemented (source)

| Capability | Route | Auth | Release state |
|---|---|---|---|
| Private status | `GET /v1/media09/press/status` | Bound service, tenant, contact_editor/admin, staging flags | Staging only |
| Form fields and privacy notice | `GET /v1/media09/press/form-spec` | Same | Non-public metadata only |
| Create Press inquiry | `POST /v1/media09/press/inquiries` | Same | Synthetic only, no outbound |
| Private inbox | `GET /v1/media09/press/inquiries` | Same | Tenant-scoped; no email/body in list |
| Private inquiry details | `GET /v1/media09/press/inquiries/{id}` | Same | Tenant-scoped; includes *synthetic* details |
| Review status | `PATCH /v1/media09/press/inquiries/{id}/status` | Same; admin required to close | `new -> reviewing -> closed`; optimistic revision |
| Public submit / send / CRM export | `POST /v1/media09/press/{public-submit,send,crm-export}` | Always 503 (service auth may first deny) | Disabled |

## Authentication, privacy, abuse and data integrity

- **Default off**, even if other engagement routes are enabled. Requires `SCEC_MEDIA09_PRESS_STAGING_ENABLED=1` plus bound principal, permitted role, tenant allowlist, dedicated Postgres configuration and `SCEC_PERSISTENCE_ENABLED=1`. If `SCEC_ENV=production`, the private routes fail closed.
- **No WordPress public endpoint** is installed; no anonymous intake, SMTP, HubSpot API client, marketing-contact sync, public Press release, CRM export, IP collection or DNS change.
- Accepts **only synthetic** `@example.org`, `@example.test` and `@example.invalid` addresses, names beginning `Synthetic `, an explicit synthetic notice version, `consent_to_reply=true` and empty `company` honeypot. This consent bit is a test fixture, **not** a lawful basis for real personal data.
- Rejects HTML markup, URLs, control characters, `@` in subject/message, unexpected fields and unbounded sizes. HTTP validation errors are redacted so submitted text is not reflected in a 422 response.
- Per-tenant PostgreSQL transactional advisory lock, five new synthetic inquiries per rolling minute; stable tenant/idempotency key makes replays safe; a changed payload using the same key returns 409.
- Both canonical records, the Press details record and audit events are created atomically. Contact `marketing_consent=false`, classification `restricted`; no automatic responses. Review updates are version-checked and auditable; closing requires an administrator. Separate roles cannot cross tenant boundaries.
- Detailed synthetic messages are stored in PostgreSQL pending isolated staging acceptance. **No actual-person data may be submitted**. Storage encryption, retention/erasure, backups, real account identity and external abuse protection remain formal blockers for real intake.
- Never use this route as a browser token workaround. Service Bearer credentials stay on the backend. WordPress form -> server-side authenticated bridge is a separate, privacy-approved activation step.

## Schema and migration

- `backend/app/persistence/media09.py` — supplemental typed metadata table keyed to the canonical Inquiry/Contact and organization IDs.
- `backend/alembic/versions/media09_1_001_press_inquiries.py` — **additive migration**, revision `media09_1_001`, parent `850_001`. Has no operational effect until explicitly applied against a dedicated, backed-up **isolated staging** DB.
- `backend/alembic/env.py` registers the metadata for migration inspection; do not apply migration to production.
- `backend/app/media09_press.py` contains domain validation, SQL-backed queue, idempotency and review operations. Router registered in existing `backend/app/main.py`, with service bearer dependency.

## Example synthetic request (restricted staging only)

```json
{
  "synthetic": true,
  "idempotency_key": "30ea459f-3c77-42ea-b8bf-881f7a094b75",
  "name": "Synthetic Press Person",
  "email": "press@example.org",
  "subject": "Request for public research methods",
  "message": "Please share the public methods summary for review.",
  "kind": "press",
  "privacy_notice_version": "MEDIA-09.1-SYNTHETIC-NOTICE-V1",
  "consent_to_reply": true,
  "company": ""
}
```

Staging requires an existing synthetic organization row and an independently issued short-lived **bound** service principal matching its `X-SCEC-Organization-ID`. Never store the bearer token in a browser, WordPress template or version control.

## Test and acceptance runbook

From the Media repository root (Python 3.11+, installed `backend/requirements-dev.txt`):

```bash
PYTHONPATH=backend pytest -q backend/tests/test_media09_press.py
PYTHONPATH=backend pytest -q backend/tests/test_media09_governance.py backend/tests/test_intake_v910.py
python -m compileall -q backend/app/media09_press.py backend/app/persistence/media09.py backend/alembic/versions/media09_1_001_press_inquiries.py
```

The unit suite checks default-off and bound identity, auth/tenant/roles, synthetic-only schema, negative fields and PII redaction, proxy/public exports denied, private queue/list/get/status dispatch, and deterministic request fingerprints. It does **not** substitute for a PostgreSQL migration/transaction test.

**Staging acceptance gate (NOT PERFORMED):** backed-up isolated Postgres, actual migration, seeded synthetic organization, signed real service identity for test environment, create -> read/list -> status transition/reopen denial, duplicate exact key, changed body conflict, 5/min rate limit, cross-tenant denial, restart persistence, DB restore/rollback, negative email/private data, no leakage in logs or responses, and regression for MEDIA-07/08/09.0. Acceptance receipts go in private Data repository, no PII.

## UI/WordPress boundary

A public-facing Media/Press inquiry form may be designed against `form-spec`, but no live WordPress form is installed or accepting people. A public bridge requires: approved privacy notice and legal basis, bot mitigation/rate limits at public ingress, signed server-to-server exchange, current SC-AUTH-02 role verification, completed retention/erasure procedures, verified backups and a separate deploy go/no-go.

**Known limitations:** no real public form, no human-login dashboard, no automatic response, no real person/contact data, no HubSpot connector, no delivery, and no PostgreSQL staging execution evidence. This source build is an engineering foundation, not a released institutional mailbox.
