# MEDIA-09.0 — Institutional CRM provider and privacy decision gate

**Date:** 2026-11-12 (America/Chicago)  
**Status:** Governance checker and review packet **IMPLEMENTED IN SOURCE**; owner/provider/privacy decisions **PENDING**. No integration or production change.  
**Tracking:** [MEDIA-09 issue #35](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/issues/35)  
**Dependency:** MEDIA-07 #31 and MEDIA-08 #33 retain independent release rights.

## Product decision

**Proposed:** treat HubSpot as an **optional CRM provider** for contacts, companies and later opportunity/follow-up records within Media's Institutional Relations capability. Keep authoritative first-party inquiries/consent with Sustainable Catalyst's existing Media/Engagement/Workspace identity boundaries. No requirement to use HubSpot to publish Press releases, write Research, manage Workspace projects, or send a newsletter.

**Not decided:** whether to open/connect a HubSpot account, purchase a paid tier, select a legal basis, accept a data-processing agreement, or export personal records. These require owner/security/privacy review; this build cannot approve them by itself.

## Repository integration findings (read-only source inspection)

| Existing component | Source role | MEDIA-09 design |
|---|---|---|
| `backend/app/contact_service.py` / canonical Contact and Inquiry models | tenant-scoped first-party contacts/inquiries, persistence gated; not a CRM adapter | **Reuse**, avoid duplicate contacts DB |
| `institutional_intelligence_v940.py` | default-off, rules-based *nonpersistent* relationship preview | Candidate classifications only, never inferred legal basis |
| `media_relations_v1140.py` | synthetic press previews, suppression and embargo; live outreach actions disabled | Press contact routing later; do not open sending |
| `privacy_consent_retention_v1060.py` | privacy/retention **draft** preview; 90-day contact draft only, no deletion or approval | Reuse policy ideas, do **not** treat 90 days as approved CRM retention |
| `partnerships_v1170.py` | synthetic partner planning, no export/federation | Approved public references only |
| `docs/handoffs/2026-11-07-PRESS-PUBLICATIONS-PRODUCT-BOUNDARY.md` | WordPress Publications, Research, Workspace and Press separated | Preserve boundary; no WP identity replacement |

Identity note: current Media code still includes legacy/staging mechanisms. Target SC-AUTH-02/UP-01 Core + Workspace authorization must be separately verified before any live CRM synchronization. No account integration is included in this increment.

## HubSpot 2026 integration assessment

- **Account-level system-to-system choice:** scoped **Service Keys (public beta)** are a candidate for single-account backend use. They do not support webhooks. If webhooks, multiple customer accounts, or user-delegated OAuth access are required, evaluate an appropriate **project-based HubSpot app** instead.
- **Legacy private apps:** new legacy private app creation was disabled in fall 2026; do not implement against a new legacy private app.
- **API versioning:** a future adapter should pin a supported HubSpot API version and discover account-required properties before writes; HubSpot's 2026-09 CRM writes enforce admin-configured validation.
- **Cost decision:** HubSpot currently advertises free tools for up to 2 users and 1,000 contacts; plan/API object availability, limits, retention, processing terms, seat and marketing-contact pricing must be rechecked against the actual account before purchasing.
- **Source references (verified 2026-11-12):**
  - https://developers.hubspot.com/changelog/service-keys
  - https://developers.hubspot.com/changelog/legacy-private-app-creation-sunset
  - https://developers.hubspot.com/changelog/crm-api-write-validation-enforcement
  - https://www.hubspot.com/pricing/crm

Do **not** provision OAuth, a service key, webhook, subscription, paid seat, or CRM data import in MEDIA-09.0.

## Governance decisions required before releasing any personal data

| Gate | Decision needed | Current disposition |
|---|---|---|
| owner_provider_choice | Use HubSpot, no external CRM, or defer; specify pilot scope and approver | PENDING |
| controller_and_rights_contact | Name accountable controller and contact route for rights/complaints | PENDING |
| purpose_and_lawful_basis | Distinguish answering press inquiries, collaboration, funding and consulting from unsolicited marketing; document lawful basis by purpose | PENDING |
| notice_and_collection_method | Approve first-party form notices, collection origins, allowed metadata, opt-out and spam controls | PENDING |
| processor_dpa_and_residency | Review HubSpot DPA, subprocessors, transfer/residency and relevant jurisdiction terms | PENDING |
| retention_erasure_and_backups | Approve retention intervals, sync deletion, legal holds, backup lag and audit minimization | PENDING |
| data_mapping_and_minimization | Approve allowlisted object/field mapping, dedupe rules and no Research data | PENDING |
| core_workspace_authorization | Confirm backend service identity, tenant/org scope, human roles, independent review and revocation | PENDING |
| vendor_security_and_key_management | Credential strategy, secret store, rotation, scopes, account ownership, webhook need and incident response | PENDING |
| commercial_terms_and_limits | Approve free/premium ceiling, contact/seat limits and lock-in/exit cost | PENDING |
| limited_pilot_scope | Define synthetic-only acceptance and separate criteria for explicit real-contact pilot authorization | PENDING |

All decisions start **pending**, and must be supported by reviewed evidence kept in an approved restricted record system. GitHub stores only opaque evidence reference identifiers, never passwords, tokens, email lists, real names/addresses or legal signatures.

## Proposed field boundaries — **not approved mappings**

- `contacts`: `email`, `firstname`, `lastname` (only as specifically approved for the relevant inquiry, not an automatic export)
- `companies`: `name`, `domain` (after source and accuracy review)
- `deals`, `tasks`: **empty in this phase**; their properties need a separate mapping and plan/permission review
- Only purpose codes: `press_inquiry_response`, `institutional_partnership`, `research_collaboration`, `funding_opportunity`, `consulting_inquiry`
- Explicitly prohibited: private Research content, unpublished Press drafts, scientific source documents, raw free-text notes, website analytics identities, newsletter subscribers, marketing consents inferred from press inquiries, and credentials

A contact inquiry does **not** imply consent to marketing or a lawful basis for unrelated CRM campaigns.

## Offline decision packet implementation

- `backend/app/media09_governance.py` implements strict stdlib validation of a **non-PII draft** packet. It has no HTTP endpoints, database connections, HubSpot imports, or deployment toggles.
- `backend/fixtures/media09_owner_decision_template.json` contains every review gate in `pending` state and every release flag set to `false`.
- `backend/tests/test_media09_governance.py` includes fail-closed unit tests: unauthorized fields, forged statuses, webhook/service-key incompatibility, invalid evidence references, email addresses in evidence IDs, duplicated purposes, unexpected release flags, and no effective authorization even when a packet claims documentary completeness.

Run from repo root in a Python 3.11+ environment:

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests -p 'test_media09_governance.py' -v
PYTHONPATH=backend python -m app.media09_governance backend/fixtures/media09_owner_decision_template.json
```

Expected default: all 11 review gates pending, `documentary_review_complete=false`, `owner_authorization_effective=false`, `hubspot_connected=false`, `external_personal_data_exported=false`, and `production_activated=false`.

**Important:** The validator checks file shape and documentary status, not signatures or reviewer authority. Even an all-approved *self-asserted* manifest never authorizes integration or real data export. A separately controlled approval service and human evidence verification are necessary. Do not use the output of this CLI as access control.

## MEDIA-09.0 exit and MEDIA-09.1 handoff

Source implementation exit: validator, tests, no-PII example, architecture/privacy packet, and cross-repository ledger in review. **Owner-approved governance exit remains BLOCKED** until all 11 decisions, including independent evidence verification, are supplied. Gate MEDIA-09.1 only to synthetic, first-party Press inquiry design until owner consent/privacy controls are approved. MEDIA-09.2 HubSpot connector, REAL imports, outbound sync, subscriber lists, sending, DNS and production changes remain disabled.

**Rollback:** This change adds isolated source and documentation only. No new router, migration, service, webhook, port, DNS, provider credential, or staging flag is installed; reverting the PR restores the source state.
