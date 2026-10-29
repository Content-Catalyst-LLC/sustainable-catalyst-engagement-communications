> SUPERSEDED DESTINATION: the owner infrastructure directive designates Raspberry Pi as development/backup. Mothership/cloud proposals below are historical and must not be executed. Use PI-CONTABO-OPERATIONAL-REPORT.md. Preserve valid tooling/tests; private production synchronization still requires explicit scope/authorization.

# SCEC-R02 technical execution results

2026-10-28. Application baseline `381a5a382c9b613136c091d0c1f235f36907c037`. **R02 NO-GO for production execution; synthetic recovery path PASS.** Primary Recovery-Key Custodian: business owner CONFIRMED, decision closed. No additional appointment confirmation requested.

## Work actually completed

- Read-only footprint: 501,747,243 bytes across all eight existing SCEC version directories; frontend uncompressed image metadata 20,983,111 bytes; nine database catalog sizes total 77,544,655 bytes. Including readable unit/config sizes, known logical footprint is **600,281,726 bytes / 572.47 MiB**. Catalog size is not logical dump size; no production dump was run. Protected configuration, role recovery metadata, TLS and unresolved artifact/session stores prevent a certified final size.
- Conservative provisional envelope: B=1 GiB per complete recovery set, 34B=34 GiB for 30 daily copies plus incoming/restore workspace. With 20% free-space reserve, require **42.5 GiB available**. Increase B if scoped metadata or actual authorized capture exceeds it. Contabo currently has 60,076,003,328 free bytes; this supports staging assessment, not approval to retain the rolling history on the production host.
- Mac internal free space 29.59 GiB is below that provisional requirement. **Recommended off-host destination: an owner-approved dedicated SCEC ciphertext allocation on existing `/Volumes/Mothership`**, observed about 4,402 GiB free, with no new subscription. This is a recommendation, not an approved path or custody arrangement. It is off-host relative to Contabo but presently attached to the same Mac; verify device identity, health, encryption, separate/offsite handling, access and independent recovery before relying on it. No directory created or volume written. Courses HD (~1,850 GiB free) is a secondary capacity candidate. Neither device is established as independent custody. `diskutil` metadata remains unavailable. Unknown replacement/rotation cost is not quoted.
- Implemented executable `tools/recovery/scec_recovery.py`, `capture_scec.py`, focused tests and a portable synthetic verifier. See `tools/recovery/README.md` for invocations, required plan/approval schemas and limitations. No scheduler, transfer mechanism or key generation is part of the production tools.

## New executed evidence

**16 synthetic GPG/recovery checks PASS**, including encryption, decryption, restored-file SHA-256, collision refusal, missing approval/recipient, source drift, ciphertext tampering even after rehash, size limit, traversal rejection, restored-content hash mismatch and failure cleanup. Decrypted PostgreSQL dump SHA-256 equals existing fixture `df98761383ee60c5f9b539af949669be16b7cae84e21d38a95da827d6164e14c`. Restore reached revision `850_001`, all 18 tables, 2 synthetic organizations and 1 contact, consistent with prior fixture evidence. GPG bundle size 8081 bytes is synthetic-only and is not a production compression estimate. PostgreSQL startup+restore took 6.2 seconds, not a production RTO certificate.

**8 collector guard/assembly tests PASS** using mocked capture commands: missing/expired approval, wrong host/database/endpoint, source drift, successful authority-bound assembly and dump-failure cleanup. Do not classify mock capture as a real backup. The existing full regression and prior R01 suites were not rerun. Initial GPG harness attempt failed during PostgreSQL startup; TCP readiness correction resolved it. Failure log is retained. Final owned container, disposable GPG keys/agent and plaintext removed; no production encryption key created or imported.

Evidence: `gpg-recovery-test.json`, `capture-guard-tests.log`, `backup-footprint.json`, `recovery-dependencies.json`. Tool SHA-256 from executed GPG verification: `58311b5a61bce6b60e6578be6d2118733bf4b1f70a2b91b19a84d1676a08fa07`.

## Infrastructure/dependency audit and R01 reconciliation

All seven existing systemd units remain active/enabled. Read-only systemd dependency records identify source-directory mount dependencies and `After=postgresql.service` on v830–v860; ordering alone is not a configured DB identity or proof that a service writes. Previously inspected runtime flags still establish the known audit baseline (persistence off/no configured DB URL), while external/manual writers remain a scope prerequisite. Candidate source uses an explicit `SCEC_HUMAN_SESSION_DB` SQLite path only when human auth is configured; no live OIDC/session store is established. The transaction foundation's SQLite database is in-memory. No mounted artifact store exists on the inventoried frontend container. Protected auth files and external writer/store ownership cannot be completed through unprivileged reads; no privilege bypass used.

Fresh live health remains v8.6.0; backend SHA `280c6b9516f9a9cafca0682f7656964077367d7d`, frontend image `sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652`, unchanged. No service, routing, grant, database or feature mutation.

R01 remains **GO to preserve the current database schema unchanged**, not GO to deploy: the distinct fingerprints are explained by 19 CHECK cast deparsing variants, tested across 380 cases; table/column/index and other exported structures matched. No corrective DDL, bootstrap rerun or migration stamp is justified. Broader data/security acceptance remains separate. R03/R08 also retain the source boundary issue: human-auth is a danger flag for the shared research/newsroom staging guard; enabling it does not integrate human sessions into those APIs. Existing regression evidence covers the flag restriction; no guard disabled or new feature built.

## Remaining technical prerequisites

Complete authorized metadata scope for unreadable config sizes/hashes, scoped DB role/privilege recovery, TLS recovery responsibility, artifacts/sessions, external writers and historical database classification. No data transfer or backup is needed for this metadata reconciliation. Produce fixed-path source/config snapshots and exact consistency checkpoint only under subsequent scope approval. A database snapshot can run without stopping writers; cross-store consistency has not been demonstrated. No writer pause is justified from empty connection metadata. Production backup, independent off-host checksum/decryption/restore, actual recovery objectives and executable inverse SCEC-only proxy patch remain unverified.

## One consolidated unresolved decision request

Primary custody is already confirmed and excluded from this request. The owner still needs to:

1. Appoint a distinct independent recovery verifier and alternate custodian, and obtain formal backup-operator acceptance; verify real separation of duties and availability.
2. Select/approve the exact Mothership SCEC allocation (or identify a specific alternative), custody/offsite handling and secure-storage controls. Confirm dedicated key-provisioning workstation/private-key and revocation storage identifiers through the restricted register. No secrets in chat/Git.
3. Approve or revise proposed daily/30-day rolling retention, RPO <=24h and RTO <=4h through formal privacy/recovery approval; these are not live policies.
4. After those controls are verified, separately authorize the reviewed dedicated GPG provisioning/import procedure and synthetic custodian recovery exercise. Key generation remains unauthorized now. Production capture/transfer/pause and deployment are not requested or bundled into these decisions; exact fixed inputs and independent evidence must precede those operation approvals.

Production remains unchanged. No new feature activation or production rollback operation occurred. Current code/image remain available; future cutover must preserve them and use a reviewed reversible SCEC-only proxy change, never database overwrite/destructive downgrade or unrelated restart.
