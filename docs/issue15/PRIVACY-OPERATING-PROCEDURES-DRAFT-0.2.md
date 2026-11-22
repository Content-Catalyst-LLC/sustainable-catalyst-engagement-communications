# SCEC operating procedures — review supplement 0.2

2026-10-28. **NOT OPERATIONAL POLICY. Production privacy gate NOT SATISFIED.** Read with the operational schedule and approval matrix. Primary and designated deputy are the same confirmed business owner; independent alternate is unappointed. Do not count two reviewers or satisfy an independent approval/coverage requirement with these assignments.

## Receipt clock and unresolved-case extensions

Retain proposed receipt-based periods: Contact 90 days, Feedback 180, Feature Suggestions 180, Channel inquiries 90, Support 365. These periods are not approved. Receipt starts the review clock; replies, edits, exports and restoration do not silently reset it. At the review date, an unresolved case needs a documented, time-limited extension approved by the operator: reference, continuing purpose, reason, hold/exception, new review date, actor and audit receipt. No indefinite or automatic extension. Expiry means review due, not authorization for deletion. Independent approval remains required wherever the final control calls for it.

## Purpose-by-purpose register — decisions pending

| Purpose | Minimum scope to assess | Basis/approval status | Required decision record |
|---|---|---|---|
| Contact response | Necessary contact and inquiry fields | Pending | Chosen basis and rationale, notice/version, recipients, period and reviewer |
| Feedback assessment | Minimized feedback; optional reply details | Pending | Anonymous/private/public boundaries, chosen basis, reuse restrictions |
| Feature suggestion assessment | Suggestion; optional attribution/reply | Pending | Attribution choice, basis, purpose/notice and retention |
| Channel inquiry | Necessary correspondence | Pending | Distinguish inquiry from subscription; approve basis and recipients |
| Support response | Necessary case/contact and justified attachments | Pending | Confidentiality, attachment access, basis, holds and processors |
| Optional newsletter/research alerts | Verified address, selected topics and consent evidence | Separate optional consent proposed; approval pending | Unticked affirmative choice, notice/version/time, confirmation and withdrawal tests |
| Audit and suppression | Minimized event/reference and suppression evidence | Pending distinct assessment | Necessity, access, exceptions, period and no secondary marketing reuse |
| Backup/recovery | Encrypted copies of approved data | Pending distinct assessment | Recovery purpose, processors/locations, period, keys and restore safeguards |

No basis is approved by this table or inferred from a checkbox. Each row needs an accountable decision, rationale, data/recipient boundary, jurisdiction assessment, notice, period, approval date and review date. Identify the responsible legal controller separately; do not infer it from the business-owner role.

## Rights intake, deadlines, exceptions and escalation

A published, accessible request channel must be chosen and verified before activation; no address or working intake is asserted here. Log receipt, requested right/purpose, tenant/reference, operator, proportionate identity verification and applicable deadlines. Do not require unnecessary identity documents, private login merely to unsubscribe, or disclose records to an unverified address. Verify delegated authority separately and deny cross-tenant access.

Proposed internal targets for review: acknowledge within 2 business days, triage and identify applicable deadlines within 5 business days, target resolution within 20 calendar days of receipt. These are **unapproved service targets, not statements of legal deadlines**. Actual controller/jurisdiction requirements must be assessed, recorded at receipt and take precedence. Do not silently restart the clock while identity verification is pending. Escalate threatened deadlines, ambiguous identity/scope, conflicting holds, processor/backups involvement, suspected incidents and operator absence. The same-person deputy provides no independent absence cover. Record reasons, approvals, permitted extensions/refusals, response and escalation route. Independent review cannot be self-approved where required.

## Consent, withdrawal, unsubscribe and suppression

Separate optional newsletter consent from inquiry/support permission and service access. No prechecked or bundled choices. Record purpose, notice/version, affirmative action, selected topics, timestamp and tenant; verify address ownership through an approved confirmation procedure before activation. Do not log raw tokens or message bodies as consent evidence.

Provide an accessible withdrawal path with proportionate verification. Suspend affected optional processing and pending deliveries while the operator resolves the request; retain only separately approved evidence needed to honor it. Inquiry handling must not create a subscription. Any future subscription message needs a tested recipient-specific unsubscribe path without a login barrier. Verify token abuse/replay behavior, queue cancellation, suppression propagation, retry handling and prevention of reimport/re-enrollment without a new approved consent event. No live mechanism is certified by this document; subscriptions and sending remain disabled.

## Backup, audit and restoration controls

Keep proposed encrypted-backup retention 30 days and audit retention 365 days **pending approval**. Owner must approve purpose, access, actual regions/processors, off-host destination, key custodian and independent recovery custodian, RPO/RTO, exceptions/holds and expiry. Encryption tools and recipients are prerequisites, not assumed installed/provisioned. Independent custody/approval requirements remain unmet by dual assignment to one person.

Maintain a versioned, minimized deletion/suppression/hold record with separately reviewed purpose and period. Quarantine restored services; reapply approved deletion, suppression and hold decisions before access, processing or outbound delivery resumes. Validate that expired backup copies, temporary restore copies and replicas follow the approved lifecycle. Document immutable-copy limits and permitted holds before promising deletion dates. No live automatic deletion/expiry is authorized. Tests must show decryption/off-host recovery, access restrictions, expiration, restore reconciliation, failure recovery and audit integrity using synthetic data first.

## Actual storage, processors, jurisdictions and WordPress flows

| Item | Current evidence | Missing evidence / decision |
|---|---|---|
| Host PostgreSQL | Administrator reports scec_engagement_v820, revision 850_001, 18 tables | Raw schema/ownership/writer metadata and comparison; actual storage/region/access/backup mapping |
| Eight other SCEC databases | Administrator reports historical verification/restore databases | Names, owners, purposes, preservation/recovery scope; do not drop or classify from name alone |
| Contabo static frontend | Running container has no artifact mounts | Controller/processor terms and actual physical location; hostname alone does not establish jurisdiction |
| WordPress | Separate public host; four published destinations verified, Feedback slug absent | Approved actual Feedback destination, plugin/form recipients, email/CRM/file flows, processors/regions/access/retention |
| OIDC/human sessions | No verified issuer/configuration identified | Authorized isolated issuer/client/identity set, cookie/session store and acceptance; no production account imports |
| Backup/off-host recovery | Synthetic PostgreSQL restore passed | Approved production scope/destination, custody, encryption, independent restore and lifecycle reconciliation |

Per flow, record source, purpose/basis, categories/minimum fields, receiving system/processor, controller role, physical location/jurisdiction, encryption, access boundary, onward processors, attachment/export behavior, periods/holds and evidence date. Preserve existing pages while independently assessing their data handling. Public notice changes require review against verified behavior before publication.

## Acceptance evidence still needed

Approve the purpose register, periods/clocks/extensions, rights channel/deadlines, notice, controller/processor/region mapping, technical custodians and independent approvals. Then execute synthetic scenarios for consent separation; withdrawal/unsubscribe/suppression and retries; rights identity/tenant denial; holds/dry-run enforcement/idempotency; backup expiry and restore reconciliation; minimized restricted audit. Record exact source, command, fixture, expected/actual result and limits. Source regressions and appointments do not certify operational workflows. Final owner approval, production privacy acceptance and activation approval remain distinct decisions.
