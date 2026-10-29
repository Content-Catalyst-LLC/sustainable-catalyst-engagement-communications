# SCEC-R02 — Final owner decision matrix and provisioning proposal

2026-10-28, America/Chicago. Application baseline `381a5a382c9b613136c091d0c1f235f36907c037`; builds on reviewed docs `50b76a8`. **R02 NO-GO. Preparation only.** GPG is the owner-directed proposed single format; key generation/import, backups, transfers, writer pause and deployment remain unauthorized.

## Dedicated key-provisioning procedure — separate approval required

1. Owner appoints the primary recovery-key custodian, independent verifier and alternate; records each individual's acceptance, recovery availability and separation of duties. Business owner is only the **proposed** primary custodian, pending explicit appointment and verified storage. Privacy primary/deputy appointments are one person and do not supply independent verification.
2. Approve a dedicated custodian-controlled offline provisioning workstation, encrypted storage and separate recovery-media locations. Verify installed GPG version and supported algorithms on both custodian and Contabo systems before generation; record compatibility without installing or changing anything under this proposal. Proposed profile: certification/signing primary key plus encryption subkey, RSA-4096 for both, one-year expiry with review/renewal beginning 60 days before expiry. This profile and expiry require approval, not silent selection.
3. Only after separate authorization, create an isolated mode-0700 GPG home on that workstation and invoke interactive `gpg --homedir "$APPROVED_KEY_HOME" --full-generate-key`. Select the approved profile, approved non-personal SCEC recovery UID, expiry and strong passphrase through local pinentry. Do not put a passphrase in commands, chat, environment, logs or Git. Verify resulting primary and encryption-subkey fingerprints/capabilities/expiry. No such command has run.
4. Record the full primary and encryption-subkey fingerprints, public export hash, UID, generation time, version, expiry and custody attestations. Independently verify the public fingerprint through a separate trusted channel. Only the approved public export may later reach Contabo's dedicated restricted backup keyring; no keyserver auto-discovery or default-keyring import. Public export/import are future approved operations, not executed now.
5. Under the approved custody plan, retain passphrase-protected private recovery material and revocation certificate offline, separately from backup ciphertext and operational access. Record storage location/access control in a restricted register, never public documentation. Alternate access requires explicit appointment and verified recovery. GPG multi-recipient encryption is not a two-person threshold scheme; do not claim dual control from a passphrase/key split without testing the approved process.
6. Independent verifier witnesses an authorized synthetic-file encryption/decryption round trip on isolated systems and confirms key recovery from designated recovery media, using no production records or credentials. Record only hashes/results and attestations. Generation success alone does not establish custody/recovery. Test expiry/rotation handling and retain old private keys until every associated approved backup/hold expires; revocation does not re-encrypt or erase older ciphertext.
7. Before operational use, approve lost-key/compromise escalation, revocation, replacement recipient verification and re-encryption/retention of existing copies. Stop backup publication on expired/revoked/unverified recipients or missing custodians. No automated bypass, plaintext fallback or unchecked overwrite.

GPG command behavior and key/subkey/expiry handling reference: [official GnuPG key-management manual](https://www.gnupg.org/documentation/manuals/gnupg/OpenPGP-Key-Management.html). Exact version-compatible command transcript will be reviewed after workstation/profile selection; this is not an execution script.

## Capacity-based destination recommendation

No production dump or archive was made to estimate compression. Main database catalog size previously reported: 8,879,127 bytes; this excludes source, images, restricted configuration, roles, artifact/session stores and historical database decisions. It is not total recovery size. Let **B** be the conservative measured bytes for one complete encrypted recovery set, including all approved stores and required immutable assets, with no assumed compression/deduplication. Initially reserve **34 × B** for 30 daily full sets, two incoming/failed-attempt slots and two restore-workspace equivalents. Keep 20% of currently free space unallocated: require **34B ≤ 0.8F**, where F is verified destination free space. Larger restore workspace or growth increases this requirement. Reference-counted image reuse can reduce cost only after a verified manifest/retention design; no such savings assumed here.

Read-only `df -k` observations on the existing Mac (no volume content inspected):

| Candidate | Available space | Approximate maximum B under conservative formula | Assessment |
|---|---:|---:|---|
| Mac internal filesystem | 29.59 GiB | 0.70 GiB | Secondary only; tight shared operating-system headroom. No directory selected. |
| Mounted `Courses HD` | 1,850.44 GiB | 43.54 GiB | Existing mounted capacity candidate, secondary until ownership, physical device/location, purpose and custody confirmed. |
| Mounted `Mothership` | 4,401.55 GiB | 103.57 GiB | Largest observed capacity candidate; secondary until ownership, physical separation and custody confirmed. |

Figures are snapshots, not reservations. `diskutil info` failed because the DiskManagement framework was unavailable; encryption, media health, filesystem characteristics and physical/external-device status are **unverified**. Volume names alone prove none of those properties. Neither volume was opened, formatted, configured or written. At B=1 GiB the conservative required free space is 42.5 GiB; at B=10 GiB it is 425 GiB. These are planning examples, not measured recovery sizes.

**Recommended primary destination:** first identify an existing independently administered off-host machine/storage allocation with measured free space meeting the formula, an approved jurisdiction, protected access and reliable restore availability. None is currently verified, so no endpoint is selected. Existing resources mean no new subscription only if quota, transfer charges and operator access are confirmed. Do not purchase storage or assume an existing cloud account. If none exists, owner may allocate an existing removable device with documented offsite custody as a separately reviewed primary option; mounted Mac volumes alone are not independent/offsite proof. Retain Mac/internal or approved external media as secondary recovery copies, subject to capacity and custody checks. Costs: no new subscription for existing local media, potential media replacement/rotation and storage/transfer costs unquoted; no paid service recommendation or purchase made.

## Proposed schedule and recovery objectives — all unapproved

- One coordinated encrypted recovery set daily, 30-day rolling retention, plus an approved pre-cutover recovery point. Proposed RPO ≤24 hours for daily backup scope and no unaccounted writes between the final deployment checkpoint and cutover. Mutable cross-store consistency must be demonstrated; `pg_dump` alone cannot establish it.
- Proposed RTO ≤4 hours after an authorized recovery declaration; feasibility unmeasured. Owner must accept targets after timed isolated recovery, not treat these as certified guarantees.
- Verify transport completion and SHA-256 on destination for every set; retain restricted manifest/operator/checkpoint records. Review key expiry, destination capacity and failed-backup alerts daily. Proposed monthly isolated recovery exercise and after any schema/storage/key change, subject to approval.
- Expire sets older than 30 days only under approved retention/hold policy and independently verified replacement/recovery coverage. An expired local copy does not prove remote copies removed. Backup retention, audit retention, legal holds, rights/suppression reconciliation and deletion evidence require formal privacy/recovery approval. No scheduled job or automatic deletion enabled.

## Scope, integrity, restoration and rollback requirements

Preserve database `scec_engagement_v820` at revision `850_001`, ownership/grants recovery metadata, reviewed source, immutable frontend image, seven SCEC unit definitions/runtime dependencies, restricted authentication/env configuration and narrowly scoped proxy recovery material. Historical eight databases remain preserved pending classification; don't silently include unrelated databases or discard history. Resolve artifact/session/object stores and every write-capable dependency before final scope approval. WordPress is a separate host and recovery scope; preserve all five destinations and require its own mapped recovery procedure before mutation.

Use authenticated encrypted transport and GPG ciphertext; verify independently retained manifest/source/image/config hashes, expected snapshot IDs/timestamps, exact destination and complete transfer before promotion from temporary names. Checksums alone do not authenticate an attacker-modified manifest. No plaintext spool on shared/public paths. Abort on wrong host/database/recipient, drift, insufficient space, dump/encryption/transfer/decryption failure, missing store, unresolved writer, missing custody or authorization.

Isolated restoration requires empty verified targets, production egress/identity/mail disabled, custodian decryption, safe tar path inspection, PostgreSQL version/revision/schema/roles and aggregate record-integrity comparisons, referenced artifact hashes, recovery of authentication configuration without using live credentials, and timed application/tenant/access checks. Reconcile suppression/deletion/holds before any later approved live processing. Prior synthetic restores are not production-backup certification.

Rollback preserves existing backend v8.6.0 and frontend v8.7 source/image/configuration and data. No destructive downgrade, in-place DB overwrite or unrelated restart. Future approved side-by-side cutover uses an exact reversible SCEC-only proxy patch with hash/concurrent-change guards. Verify old routes/version/auth after reversal before stopping only the new candidate. Any later approved writes require a separately approved data-recovery/RPO decision; code rollback alone is insufficient. Current preparation needs no production rollback.

## Final owner decision matrix

| Decision | Proposed position | Current state / evidence required |
|---|---|---|
| Encryption format | GPG only | Owner directs proposal; execution not authorized. |
| Key profile/UID/expiry and provisioning workstation | Dedicated RSA-4096 primary + encryption subkey, one-year expiry | PENDING approval and compatibility review; no generation/import. |
| Primary recovery-key custodian | Business owner | PENDING explicit appointment, acceptance and verified secure storage. |
| Independent recovery verifier | Separate individual | UNAPPOINTED; identity/acceptance/independence required. |
| Alternate custodian | Separate authorized individual | UNAPPOINTED; contingency access and secure storage required. |
| Primary destination | Existing independently administered off-host allocation first | PENDING exact endpoint, capacity B/F, jurisdiction/access/cost and recovery verification. |
| Secondary destination | Owner-selected Mac/existing approved media | PENDING exact directory/device, capacity, encryption and separate custody. |
| Retention/schedule | Daily full recovery set, 30-day rolling | PENDING formal privacy and recovery approval; no expiry/deletion job. |
| Recovery objectives | RPO ≤24h; RTO ≤4h; pre-cutover checkpoint | PENDING owner acceptance and timed validation. |
| Complete scope / consistency / writer controls | Non-disruptive where equivalent recovery proven | PENDING store/writer reconciliation; no pause commands authorized. |
| Key provisioning execution | Separate owner approval after prerequisites | NOT AUTHORIZED. |
| Production backup / transfer / writer pause | Separate exact-command approval after preparation | NOT AUTHORIZED. |
| Deployment / feature activation | All applicable gates and separate cutover approval | NOT AUTHORIZED; R02 and overall production NO-GO. |

No new broad suite, cryptographic round trip, production backup/restore or deployment was executed for this document. Verification performed: read-only capacity metadata, existing inventory review and documentation checks only. Production services, data and authentication remain unchanged.
