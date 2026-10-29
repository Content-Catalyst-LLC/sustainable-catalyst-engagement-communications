# SCEC-R02 — Guarded execution plan and read-only findings

2026-10-28. Reuses recovery tooling/synthetic evidence at `ca2f08e`; no synthetic tests repeated and no production tool changes. **Primary recovery-key custody CONFIRMED/CLOSED. R02 production execution NO-GO.** This is an operational runbook/evidence update, not another owner-review package.

## Read-only findings

Mothership: `/dev/disk4s2`, journaled HFS+, mount flags `local,nodev,nosuid,journaled,noowners`; total 8,001,219,248,128 bytes; available 4,726,131,449,856 bytes. Capacity exceeds the provisional 42.5 GiB requirement (1 GiB/set, 30-day retention plus workspace/reserve). **Capacity PASS for that provisional envelope; filesystem/access protection NOT CERTIFIED; encryption and hardware health UNVERIFIED.** `diskutil info` failed with unavailable DiskManagement, `system_profiler SPStorageDataType` returned an empty result, `ioreg` failed and smartctl is absent. No filesystem verification, repair, SMART self-test, mount change, encryption change or volume write was run. Journaled status is not a health certificate. `noowners` does not establish suitable ownership enforcement. Do not archive restored private data onto this mount based on free space alone.

Recommendation remains an approved SCEC ciphertext allocation on existing Mothership for no new subscription, **conditional on verified protected storage and physical/offsite handling**. No path created or selected as authorized. Do not automatically enable ownership, format, repartition or create an encrypted container. Device health/encryption must be checked by an authorized Mac operator with working DiskManagement/appropriate device access; unavailable metadata is not a failed disk or proof of no encryption.

Protected configuration: reused administrator report hashes for v800.env/v860.env, with no DB targets configured. Exact known hashes are in `protected-scope-reused-evidence.json`. Existing report SHA-256 was verified remotely. Non-interactive sudo execution is unavailable; no password or privilege bypass attempted. Therefore configuration sizes/modes/storage paths and root/database-native writer metadata **remain BLOCKED**, not complete. A read-only metadata-gap script is staged at `/home/catalystadmin/scec-issue15-recovery-metadata/admin-r02-scope-completion.py`, SHA-256 `5bc2f78fa1506451e3fbcf15fd6a78ea35393cc8a02014e448bce5a3e3c7ef95`. It emits only config names/hashes/size/mode, safe store identifiers, candidate job hashes, extension/trigger/subscription metadata and aggregate TLS-storage sizes. It never reads private-key contents, emits secret values or performs a backup/service operation. Reviewed source is included with these deliverables. Syntax compiled; privileged execution has not occurred.

Authorized administrator command (read-only; no backup permission implied):

```bash
umask 077
sudo python3 /home/catalystadmin/scec-issue15-recovery-metadata/admin-r02-scope-completion.py > /home/catalystadmin/scec-issue15-recovery-metadata/r02-scope-completion.json
```

Audit-account cron contains one entry referencing `/opt/sustainable-catalyst/cron/run-wordpress-cron.sh`, with no literal SCEC reference and possible external execution. Its file hash and entry hash were recorded; no command executed. Treat this as a WordPress dependency to preserve, not a candidate SCEC stop target. No SCEC-named timers observed. Root, indirect and external/manual writer completeness still requires authorized metadata and operator attribution. Empty connections or name searches do not close that scope.

## Exact ordered execution procedure — blocked inputs must be resolved first

Existing tools: `tools/recovery/capture_scec.py` and `scec_recovery.py` from `ca2f08e`. `capture-plan.blocked.json` and `backup-approval.blocked.json` intentionally fail closed: no recipient, DB backup identity, staged-file hashes, approved destination, checkpoint or authority is invented. The Unix socket shown is a proposed host-local service profile, not a verified granted backup identity.

1. Complete metadata scope. Attribute every SCEC writer/store and distinguish historical DBs from required recovery scope. Current collector is for **main database only**; preserve all eight historical DBs unchanged and separately approve any additional capture scope. Map the narrow SCEC TLS/proxy recovery responsibility without including unrelated sites. No whole-host/shared-Postgres backup or cron/service stop is implied.
2. Verify storage protection, named independent verifier/alternate/operator acceptance, restricted scratch and approved key custody. Provision/import a production recipient only after separate key-operation approval; no such approval exists now. Approve retention/recovery objectives. Do not install a schedule or expiration job.
3. After exact backup authorization, prepare fixed-path source/config/runtime and scoped role/grant metadata in encrypted-at-rest restricted scratch (0700 directory, 0600 files). Include the eight inventoried source/runtime roots, seven unit definitions, v800.env/v860.env, narrowly scoped Caddy route/auth recovery and all confirmed SCEC artifact/session material. Preserve modes/ownership/ACL metadata inside the source archive. Never tar a live PG data directory, blindly dump all cluster roles/password hashes, or collect unrelated TLS keys. No such archive has been created.
4. Finalize the capture plan with approved staging directory, public-key-only GPG home/full fingerprint, verified libpq service profile/user, exact file hashes, immutable image ID and calculated free-space requirement. Final approval must bind the final plan SHA-256, host, expiry, actual authority and independent verifier, complete scope and consistency checkpoint. Approval JSON documents human authorization; it is not itself cryptographic proof of approval or independence.
5. Only then run on `vmi3544820` using the approved account/privilege boundary:

```bash
python3 tools/recovery/capture_scec.py --plan /APPROVED/final-capture-plan.json --approval /APPROVED/backup-approval.json
```

The tool checks plan authority/host/expiry, DB identity/version/revision, source hashes/capacity and immutable image; creates a custom DB dump with ownership/grants retained and pinned image archive; encrypts the hash-manifest bundle; and removes its temporary staging on exit. Existing output is refused. No writers are paused. Use a non-disruptive transactional PG snapshot only after the store map establishes equivalent whole-system recovery. If mutable cross-store consistency cannot be guaranteed, stop and prepare exact SCEC-only drain/resume controls for separate approval; none are invented here.

6. Independently record the ciphertext SHA-256 in an approved audit channel. Only after exact destination/transfer approval, copy ciphertext and the approved manifest to the selected off-host allocation using authenticated transport. A sidecar copied alongside attacker-modified ciphertext is not independent integrity evidence. Compare source/destination size and SHA-256; do not promote incomplete copies. **No transfer command is finalized before an approved destination directory and transport identity exist.** No production-data transfer has run.

## Independent restore procedure

The verifier must be a distinct appointed person; the same-person privacy primary/deputy roles do not satisfy this. Choose an approved isolated recovery machine/context, with restricted encrypted scratch, approved custodian key access, no production DNS/identity/mail/webhook routes and no production Docker daemon. No independent target is yet approved; never substitute the live database or the default production Docker context.

First custodian decrypts with the existing verified command, using an independent expected checksum:

```bash
python3 tools/recovery/scec_recovery.py restore --bundle /APPROVED/offhost-bundle.tar.gpg --sha256 INDEPENDENT_APPROVED_SHA256 --gpg-home /APPROVED/custodian-keyring --recipient APPROVED_FULL_FINGERPRINT --target /APPROVED/fresh-isolated-restore --max-bytes APPROVED_MAXIMUM_TAR_BYTES
```

This verifies ciphertext before decryption, then integrity, safe archive paths, member sizes and every file hash; it refuses existing targets and removes failed staging. It does not start restored services or connect to any database. Scratch must protect temporary plaintext, including abrupt power-loss leftovers; normal unlink is not secure erasure.

For PostgreSQL verification on the selected isolated daemon, use the pinned PostgreSQL image `sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54`. Create only a UUID-named container with `--network none --memory 512m --cpus 0.5 --tmpfs /var/lib/postgresql/data:rw`, no mounts/ports and a fresh synthetic bootstrap password supplied in a restricted env file. Wait for `docker --context APPROVED_ISOLATED_CONTEXT exec OWNED_CONTAINER pg_isready -h 127.0.0.1 -U postgres` before loading. The exact verified restore command shape is:

```bash
docker --context APPROVED_ISOLATED_CONTEXT exec -i OWNED_CONTAINER pg_restore --exit-on-error --no-owner --no-acl -U postgres -d scec_isolated_recovery < /APPROVED/fresh-isolated-restore/database.dump
```

`--no-owner --no-acl` is only for the isolated verification role; scoped production ownership/grant metadata remains retained separately and must be reconciled before real recovery. Record revision `850_001`, structural comparison, aggregate integrity/counts and artifact references privately. Load/test the recovered frontend image only in this approved isolated daemon; verify immutable image ID and start with no production secrets or external connectivity. Inspect source/config metadata without running real authentication secrets. Reconcile approved suppression/deletion/holds before any later live processing. Measure full recovery time; the prior 6.2-second synthetic startup/restore does not certify a 4-hour production RTO.

Abort on target/daemon ambiguity, wrong host/profile/database, missing/unverified recipient/custody, drift, incomplete scope/checkpoint, insufficient capacity, dump/encryption/transfer/decryption/hash/schema/object failure, unexpected egress or missing approval. Remove only UUID-owned verification resources; never stop shared or old production services. Preserve restricted diagnostics. Since no writers are paused by these tools, there is no automatic resume operation. Any later approved quiescence needs its own recorded original-state/resume plan.

## Rollback and current GO/NO-GO

Preserve current source `280c6b9516f9a9cafca0682f7656964077367d7d`, v8.6.0 service and frontend v8.7 image `sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652`. A future side-by-side cutover requires a reviewed exact SCEC-only proxy diff and inverse with concurrent-change guards, Caddy validation and authorized reload. No inverse patch can be truthfully supplied until that forward diff exists. Never overwrite DBs or run destructive downgrade. Later authorized writes require a separately approved data-recovery/RPO decision.

R01: **GO preserve schema unchanged**, 19 cast variants already explained/tested; no DDL. R02: **NO-GO**, pending storage protection/health, metadata/writer closure, unappointed verifier/alternate, operator acceptance, retention/objective approval, separately authorized production-key provisioning, actual backup/off-host independent restoration and rollback evidence. Primary custody is confirmed and is not an open decision.

All genuinely unresolved owner decisions remain grouped: independent people/operator acceptance; exact protected off-host allocation and isolated restore host; provisioning workstation/key-storage/profile authorization; retention/RPO/RTO approval. The metadata command and Mac checks are operator evidence tasks, not another custody decision. Production backup, transfer, writer pause and cutover require later exact-operation approvals and are not requested by this runbook. No completed synthetic tests rerun, no production key generated/imported, no production data transferred or backed up, no services changed or features activated.
