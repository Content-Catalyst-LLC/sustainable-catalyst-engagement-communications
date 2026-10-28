# SCEC Operational Privacy & Retention Schedule

**UNAPPROVED OWNER-REVIEW DRAFT — 2026-10-28. No processing or deletion authority.**

Applies to the proposed SCEC v12.2 service, not retrospective authorization for existing WordPress forms or other systems. Owner confirmation: no operational schedule, privacy operator, withdrawal/unsubscribe process or retention/deletion enforcement has been verified. The privacy production gate is **NOT SATISFIED**. Source: `backend/app/privacy_consent_retention_v1060.py`, policy `10.6.0-draft` at the pinned merged commit. The published July 14, 2026 Privacy Policy gives general principles and does not approve these periods.

| Channel | Proposed purpose | Draft days |
|---|---|---:|
| Contact | Respond to inquiry | 90 |
| Feedback | Evaluate feedback | 180 |
| Feature Suggestions | Evaluate suggestion | 180 |
| Channel inquiries | Manage inquiry | 90 |
| Support | Respond to support request | 365 |

**Clock decision required:** existing simulation computes receipt + days. Proposed initial rule retains that receipt-based clock; an unresolved matter at its review date goes to the operator for a documented, time-limited extension. No silent reset on every edit. Owner must approve the clock, exceptions and lawful basis separately for every purpose before collection or persistence. Expiry means review due, not permission for immediate automatic deletion.

## Proposed operating procedure

1. Before submission, show a versioned purpose notice, controller/contact, fields required versus optional, data location/processors, proposed retention and rights route. Collect only necessary fields. Separate optional newsletter consent from permission to reply; no prechecked boxes or bundling. Record notice/purpose/basis version, affirmative action, timestamp, channel and tenant; never log message bodies or credentials as consent evidence. A checkbox alone does not establish a lawful basis. An owner-approved basis register is required per purpose.
2. For newsletter subscription, require a verified address and owner-approved confirmation process, record requested topics and consent version, and keep delivery disabled until deliverability and unsubscribe certification. Research inquiry submission must not register a subscriber.
3. Withdrawal requests use a verified, accessible channel and proportionate identity verification. Suspend the affected optional processing and suppress pending delivery while the operator resolves it; retain only approved evidence necessary to honor the request. Do not require login merely to unsubscribe. Withdrawal does not silently delete records retained for another documented purpose.
4. Every future subscription message must contain a tested recipient-specific unsubscribe path with no login barrier. A minimal suppression record prevents reimport or queued redelivery. Token design, abuse protections, expiry/replay behavior, queue cancellation and suppression propagation require isolated testing. No live endpoint or outbound mail is authorized by this proposal.
5. Access, correction and deletion requests enter a restricted case log, with receipt, verification outcome, scope, decision, completion evidence and response. Operator reviews holds and exceptions. Remove or deidentify approved primary records and derived/search/cache copies; verify counts and tenant scope. Reject cross-tenant requests. No automatic deletion until policy, implementation, authorization and restore behavior pass.
6. Proposed enforcement: daily **dry-run** due-record report reviewed by the operator; deletion remains a separate authorized job. Approved enforcement later uses bounded batches, legal-hold exclusion, idempotent request IDs, audit receipts, failure alerts and stop controls. No policy approval or job activation through a synthetic preview API.
7. Proposed backup schedule for review: encrypted daily backups retained 30 days; no indefinite snapshots. Owner must approve RPO/RTO, storage location, access, key escrow, exceptions and expiry. This is a new proposal, not current practice. Immutable backups age out through the approved lifecycle; on restoration, quarantine the restored service and reapply suppression/deletion/hold records before allowing access or outbound processing. Keep restore evidence without unnecessary personal data. A 30-day proposal must be reconciled with deletion promises and other retention duties before approval.
8. Proposed audit log: event ID, tenant, actor reference, policy version, action, reason, record-reference hash, timestamp, result and approval reference. Keep raw tokens, passwords, inquiry text and full email addresses out of logs. Proposed audit retention 365 days is also **unapproved**, requiring minimization and access review. Log retention is distinct from source-record retention and backup retention.

## Accountable roles and approval record

Owner must appoint a named privacy operator and deputy, identify the responsible controller, approve the purpose/basis register and notice, assign engineering enforcement and backup-key custodians, and define escalation and response deadlines. No individual is appointed by this document. Operator responsibilities include request handling, exceptions/holds, retention reviews, suppression reconciliation after restore, processor inventory, access review, incident escalation and signing verification evidence.

Approval table to complete: policy version; owner/operator/deputy; lawful basis per purpose; clock and periods; backup/audit periods; holds; rights response deadlines; jurisdictions/locations/processors; approved notice; approval date; review date; implementation evidence; test evidence. Every field is presently pending.

## Reconciliation with the public Privacy Policy

Prepare reviewed wording or a linked SCEC schedule explaining the specific purposes, chosen clocks/periods and exceptions, separate newsletter consent, practical withdrawal/unsubscribe and rights routes, accountable contact, processing locations/providers, backup expiry and restoration safeguards. Confirm these claims match implemented behavior. Obtain owner review before publication; this draft does not edit the public policy, WordPress pages or forms. Keep collection, production persistence, subscriptions, outbound messaging and automatic deletion disabled until applicable procedures are approved and verified.
