# Media privacy operations — implementation and synthetic acceptance

All privacy records stay in the existing Media PostgreSQL database. No new CRM, authentication service or production database is introduced. Real processing and destructive jobs remain disabled by default. The owner-proposed schedule is a configuration candidate, not legal approval.

## Controls

- **Retention:** spam/invalid 30 days; routine closed inquiries 12 calendar months after last substantive correspondence; active inquiries reviewed after six months; relationships reviewed annually and expire after 24 months without meaningful activity. A reviewed continuing-purpose exception requires an administrator, an opaque evidence reference and expiry within the annual review interval. Assignments, note edits and status changes do not extend correspondence retention. Unreleased legal holds always block deletion, including overdue holds.
- **Rights:** protected administrator desk at `/press/privacy`; public synthetic intake at `/press/privacy/rights`. Acknowledgment is distinct from marketing/CRM consent. Requests track one-calendar-month due dates, a justified bounded extension, independently verified contact scope, access/structured-copy review, correction, restriction/objection, erasure and external-response evidence. Verification and responses are human operations; no identity-document upload or automatic email is implemented or claimed.
- **Erasure:** Media Contact/Inquiry/detail/follow-up records, owned attachment files, linked historical audit events and rights PII are removed or scrubbed in scope. Other-purpose canonical references block full contact erasure and require their owning workflow's review. Retention can remove an eligible Media inquiry while preserving a contact still needed by another workflow. Unreconciled CRM exports block local completion; synthetic mock exports can be explicitly acknowledged only in synthetic acceptance tools. No arbitrary path or shared-product deletion is attempted.
- **Receipts:** independent random receipt, tenant, counts, reason and time; no email, body, contact/inquiry UUID or staff subject retained in the replacement receipt. Closed rights correspondence has its own configured retention. HMAC suppression markers are restricted pseudonymous records, not claimed to be anonymous.
- **Backups:** register managed backups under opaque UUID filenames with signed sidecars, content hash, expiry and suppression generation. Expired backups cannot be restored through the guard, and copied-back expired files are deleted on the next approved expiry run. Unreleased holds conservatively retain full-database backups. Suppression is signed and persisted outside database backups before destructive work. Database-generation mismatch blocks normal Media/canonical reads and writes after a failed transaction or old restore. A reviewed recovery command applies prior signed deletion decisions before service resumes.
- **Minimization:** marker compaction requires approved complete backup coverage and a configured approved policy, preserves markers while earlier managed backups survive, refuses unregistered dumps, and permanently refuses restores older than the supported suppression window. Receipt retention is configurable. Media-owned rotated log files can expire after a configured 30–90 days; shared host journals, provider snapshots and unregistered copies require explicit operational coverage before production approval.
- **Optional HubSpot:** staff connection-status endpoint and administrator-only manual contact/company synchronization. Company mapping uses the current tenant's canonical organization name and reviewed domain; durable outcome stays in existing PostgreSQL. Credential and separate CRM privacy authorization are mandatory. No newsletter or private Research mapping. Tests use mock transports only.

## Configuration and operator commands

Existing `SCEC_DATABASE_URL`, tenant allowlist and platform identity remain authoritative. Privacy operations require `SCEC_MEDIA09_PRIVACY_ENABLED=1`, a mode-0600 `SCEC_MEDIA09_PRIVACY_KEY_FILE`, an absolute `SCEC_MEDIA09_SUPPRESSION_FILE` in a mode-0700 directory outside database backups, and protected mounted attachment/backup/log roots. These are operator-supplied locations; no production credential or identity path is invented. Retention policy: `SCEC_MEDIA09_RETENTION_POLICY_FILE`, using `backend/fixtures/media09_retention_policy.example.json` (disabled, unapproved).

Never initialize over a missing historical ledger. Initialization is restricted to an explicitly marked new synthetic baseline. Production onboarding requires the verified operational baseline and protected key/ledger custody; a database-only backup is insufficient.

Manual operator commands run in the existing backend environment:

```sh
PYTHONPATH=backend python -m app.media09_privacy_cli preview --organization "$SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID"
# Only after approved scope and configuration; defaults remain disabled:
PYTHONPATH=backend python -m app.media09_privacy_cli retention --organization "$SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID" --apply
PYTHONPATH=backend python -m app.media09_privacy_cli expire-backups --organization "$SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID" --apply
PYTHONPATH=backend python -m app.media09_privacy_cli restore-suppression --organization "$SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID" --apply
```

`register-backup`, `expire-logs`, and `compact-suppression` use the same CLI and explicit `--apply`. Synthetic-only log/backup acceptance uses `--synthetic-only`. No automatic timer or real deletion is activated by installing the code. The approved deployment must schedule and monitor the reviewed maintenance commands, inventory every actual backup/log location, and verify recovery before opening real collection.

Real release now also requires `privacy_controls_acceptance_ref` in the protected approved notice, enabled privacy controls and an enabled, approved operational retention policy. Real erasure additionally requires `SCEC_MEDIA09_REAL_ERASURE_ENABLED=1`. These are references to independently obtained approval, never substitutes for it. Staff sign-in stays disabled until the single Platform Core HTTPS issuer/client/credential-mount blocker passes.

## Acceptance

`backend/tests/test_media09_privacy_pg.py` runs only with an explicit `MEDIA09_PRIVACY_TEST_DATABASE_URL` ending in the dedicated synthetic acceptance database name. It exercises actual PostgreSQL, owned attachment deletion, role/tenant/CSRF denial, rights verification/access/correction/restriction/response, holds, calendar boundaries, shared-reference denial, forced-rollback suppression recovery, actual `pg_dump`/`pg_restore` suppression, backup expiry, log expiry and marker minimization. Unit tests cover signatures, custody, path traversal/symlinks/hardlinks, notice acknowledgment and default-off gates. Existing full backend, PHP and JavaScript checks remain required.

Clean public notice candidate: `docs/public-candidates/MEDIA09-privacy-notice.md`. Exact original review: `docs/MEDIA09-owner-release-review.md`. Owner decisions still required are listed separately in `docs/MEDIA09-NOTICE-VERIFICATION.md`; no candidate has been activated as public policy.
