# SCEC guarded recovery tools

No tool creates keys, transfers bundles, pauses writers, changes services, migrates production or activates features. Shipping these tools grants no execution authority. Production capture remains blocked by explicit scope, custody, consistency and destination approval. Primary recovery-key custody is confirmed and closed.

## Executable entry points

Python 3.11/3.12, GPG 2.4.4 and PostgreSQL 16 client compatibility were observed. No additional Python dependency is needed. Use a dedicated restricted GPG home with an independently verified full recipient fingerprint. Only disposable keys were used in validation. Exact recipient pinning supplies operator trust in that isolated keyring; no keyserver discovery or short-ID lookup is used. Approval JSON is an operator attestation, not a signature verification service or proof of a person's independence. Verify real approval and identities outside the program.

```bash
# Future approved production capture; plan and approval must already exist.
python3 tools/recovery/capture_scec.py --plan /APPROVED/capture-plan.json --approval /APPROVED/backup-approval.json
# Verify the destination checksum against a separately retained approved manifest before restoring.
python3 tools/recovery/scec_recovery.py restore --bundle /APPROVED/bundle.tar.gpg --sha256 APPROVED_SHA256 --gpg-home /APPROVED/custodian-keyring --recipient APPROVED_FULL_FINGERPRINT --target /APPROVED/new-isolated-restore --max-bytes APPROVED_MAXIMUM_UNCOMPRESSED_TAR_BYTES
```

Placeholders intentionally fail; do not copy them into a production session as authorization. Restore target must not exist. `--max-bytes` must cover tar overhead and measured data, while fitting the sandbox capacity. Decryption completes and validates GPG integrity before archive parsing; archive traversal, links, duplicate members, unlisted members, wrong sizes and wrong file hashes fail closed. Temporary plaintext requires approved encrypted scratch storage; normal unlink is not secure erasure on SSD and abrupt power loss may leave staging files. No startup of restored credentials/configurations occurs.

`capture_scec.py` requires a pinned, pre-prepared source archive and scoped role/grant recovery metadata. It does not guess missing source/store scope or create a generic all-host globals dump. Required plan fields:

- `mode="production"`, `hostname`, `label`, `gpg_home`, `recipient`, `output` (absolute new file in mode-0700 directory), `minimum_free_bytes` (approved staging/bundle capacity budget).
- `database="scec_engagement_v820"`, `revision="850_001"`, `pgservicefile` (mode0600), `pgservice`, `db_host`, `db_port`, `db_user`; service file values must match. Credentials remain in restricted libpq files, never CLI/logs/Git.
- `image` immutable SHA-256, `source_archive_name`, `roles_metadata_name`, `capture_files=[{"name":"safe-name","path":"/absolute/fixed-file","sha256":"approved-hash"}]`. Include all approved unit, configuration, source/runtime, artifact/session and narrowly scoped proxy recovery files. Preserve ownership/mode/ACL metadata within the pre-prepared archive. No live PostgreSQL data-directory tar.

Approval file fields: `operation="SCEC_BACKUP_ONLY"`, exact `plan_sha256`, `hostname`, timezone-aware future `expires_utc`, `owner_approval_record`, `independent_verifier`, `scope_complete`, `consistency_checkpoint`, `custody_verified`, `destination_approved`. Production capture checks approval/host/expiry, libpq identity/revision/version, source hashes, capacity and immutable image syntax. It runs `pg_dump -Fc --lock-wait-timeout=10s` with ownership/grants retained and saves the pinned image. Capture subprocess failures remove owned staging; GPG bundle output collisions and source drift are refused. No cross-store consistency is inferred from these guards; an approved checkpoint/change freeze must establish it beforehand. The derived file-hash inventory explicitly retains the original approved plan digest; it is not a new owner approval.

`backup` can bundle already-prepared fixed files using `scec_recovery.py backup --plan PLAN --approval APPROVAL`; plan uses `files` instead of `capture_files`. Synthetic mode bypasses production attestations only for explicitly supplied synthetic fixtures and labels starting `SYNTHETIC-`. Labels do not inspect or prove data provenance. Operators must never mislabel real records to bypass approval.

## Reproduce focused synthetic verification

```bash
python3 -m unittest discover -s tools/recovery -p test_capture.py -v
python3 tools/recovery/verify_gpg_remote.py --ssh-target AUTHORIZED_TEST_HOST --identity /APPROVED/ssh-identity --fixture-root /APPROVED/existing-synthetic-fixture --evidence /APPROVED/new-evidence.json
```

The remote verifier requires an existing synthetic `postgres-result.json` and hash-matching `synthetic-postgres-fixture-*.dump`, GPG and the already available pinned PostgreSQL image. It creates disposable **test-only** RSA2048 encryption keys with one-day expiry and no passphrase, for unattended fixture validation; these settings are never the proposed production key profile. It creates one UUID-named `--network none`, resource-limited PostgreSQL container with tmpfs storage and no bind mounts or published ports. Readiness uses TCP loopback to avoid the temporary initialization socket. It decrypts the synthetic dump, verifies hashes, restores it, checks revision, table/fixture counts and failure paths, then removes its container, temporary keys, agent and plaintext. A previous first attempt failed at startup; corrected readiness and final results are retained separately.

The restore command extracts verified files only; database loading occurs only inside the verifier's owned isolated container. A future authorized production-data restore must similarly use a fresh isolated target, disabled egress/real identity/outbound processing and a custodian, with scoped grants/configuration and referenced object checks. No bare `pg_restore` against a production service profile is supplied. Retain and independently approve the manifest checksum outside the backup destination; an attacker replacing ciphertext plus sidecar is not detected by a sidecar alone.

## Scope of evidence

Real GPG encryption/decryption and PostgreSQL restoration were executed on synthetic data. Collector tests mock `psql`, `pg_dump`, image saving and bundling: they verify guards/assembly/cleanup, not actual production capture or image recoverability. Existing R01 structural/semantic evidence is reused. No production recovery, off-host transfer, independent human verification, RPO/RTO or rollback certification is claimed. Never delete older recovery copies automatically under this tool.
