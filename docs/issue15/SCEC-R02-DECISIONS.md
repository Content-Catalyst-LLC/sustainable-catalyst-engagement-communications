# SCEC-R02 — Recovery encryption, destination and custody decisions

2026-10-28. **NO-GO for production backup/cutover. Encryption, destination and independent custody: PENDING.** Baseline: `381a5a382c9b613136c091d0c1f235f36907c037`. Preparation only; no keys created, private keys accessed, production records transferred, backups run, writers paused or services changed.

## Public-key inventory and authority

Read-only SSH inventory of Contabo `vmi3544820` as `catalystadmin`: `/home/catalystadmin/.gnupg` does not exist. No GPG initialization was attempted. No armored public-key files were found in the checked immediate recovery metadata, v122015/v122016 staging directories or readable engagement configuration location. This limited scan does not establish absence elsewhere. Root's public keyring and unreadable protected locations remain uninspected; administrator public-only inventory is needed if an existing key may be held there. No public fingerprints or user IDs were observed in this scope; no public-key file was identified. **No key is explicitly authorized for SCEC recovery.** Presence alone would not authorize one.

GPG is installed at `/usr/bin/gpg`; age, rclone, restic and borg are absent. Evidence: `public-key-inventory.json`. No private-key listing or export is needed.

## Consistent encryption recommendation — owner selection pending

Use the installed GPG tool for the coordinated encrypted artifacts, replacing the earlier age command forms. Pin the owner-approved full fingerprint and a reviewed public-key file in an isolated backup keyring; independently verify fingerprint, encryption capability, validity and custody before use. Do not silently import into an operator's default keyring, fetch keys from a server, weaken trust checks or use short key IDs. The backup operator needs only the public key. Private recovery material remains with the separately appointed custodian in an approved location. Select one format for database, configuration and image artifacts; do not claim an untested age/GPG combination has a verified recovery path.

No recipient exists in this procedure yet. Key creation/import, tool configuration, backup execution and custodian decryption testing require the subsequently approved procedure. A GPG integrity-protected encrypted stream plus SHA-256 transfer verification is necessary but does not prove origin or successful recovery. Independently retain/approve the manifest and test actual decryption and restoration. Do not introduce an unapproved signing key.

## Off-host options — no destination selected

| Option | Verified availability / storage | Encryption and access | Retention and recovery | Expected incremental cost |
|---|---|---|---|---|
| Existing Mac, owner-selected restricted directory | Physically separate from Contabo; current filesystem has about 30 GiB available. No backup directory selected; artifact sizes/headroom not yet established. | GPG ciphertext only; local access permissions and disk encryption status unverified. No private key copied alongside backup. | Owner approves period and independent copy; connected same-owner laptop alone does not establish independent custody or disaster resilience. Verify ciphertext hash and custodian restore in isolation. | No new service subscription; additional storage may be needed, cost unknown. |
| Existing separately administered off-host server or storage account, if owner identifies one | No endpoint, account, bucket, quota, jurisdiction or recovery access verified. Contabo's own disk is not off-host. | Transport authentication, restrictive storage policy, GPG ciphertext, independent access and deletion controls must be verified. | Require approved retention, expiry/hold process and restore access surviving loss of Contabo. | Existing plan/quota/transfer charges unknown; no purchase authorized. |
| Owner-supplied encrypted removable storage held separately | No device, capacity or custodian verified. | GPG ciphertext plus approved device/access controls; protect against loss and unauthorized deletion. | Offsite custody and recurring rotation needed; independent restore evidence required. | Existing-device cost may be zero; procurement cost unquoted/unapproved. |

Only the Mac is presently observed as an available off-host machine; no cloud destination is claimed. No remote storage credentials or production data were inspected to infer an endpoint. A folder's existence would not establish owner authorization, retention, jurisdiction or independent control. The privacy draft's 30-day backup and 365-day audit proposals remain unapproved.

## Recovery custody and independent approval matrix

| Role/control | Current candidate/evidence | Status / required acceptance |
|---|---|---|
| Business owner / scope approver | Existing owner | Must select recipient, destination, RPO/RTO, retention and execution scope. |
| Primary and Deputy Privacy Operator | Business owner in both roles, explicitly confirmed | One individual; not two independent approvals. |
| Backup operator | Existing authorized Contabo administrator is a possible candidate; previous inventory execution demonstrates technical access only | Human identity, acceptance, least privilege and availability pending. `catalystadmin` is an account, not an appointment. |
| Recovery private-key custodian | None appointed | PENDING; explicit acceptance and recovery-key location/access process required; no private material in chat/Git. |
| Independent recovery approver/verifier | None verified | PENDING; identify a distinct individual and define required approvals. Administrator may qualify only after identity, independence and acceptance are confirmed. |
| Independent alternate custodian/operator | None appointed | PENDING; document contingency and access recovery. |
| Separation of duties | Same-person privacy appointment supplies no independence | NOT SATISFIED where required; no self-approval substitute. |

## Owner decisions needed before executable procedure

1. Choose an existing authorized GPG public-key file and full fingerprint after independent verification, or separately authorize a key-provisioning plan. No key generation is requested/executed now. Confirm GPG as the single proposed format or request another reviewed approach.
2. Select an exact off-host destination: restricted Mac directory only if measured size/headroom and protection meet requirements, or identify an existing separately administered endpoint/device. Confirm storage owner, region/jurisdiction, access, retention, expiration, cost and recovery availability.
3. Name and obtain acceptance from backup operator, private-key custodian, independent approver/verifier and alternate. Explicitly record distinct-person controls and any unresolved independence.
4. Approve recovery targets and final scope only after all writers/artifact/session stores and restricted configuration recovery are mapped. Production database is `scec_engagement_v820`, revision `850_001`; preserve the eight historical SCEC databases pending classification.

These selections do not authorize backup execution, writer pause or deployment. After selection, finalize fixed-path commands, target guards, encryption failure handling, checksums, manifest, independent restore and exact abort/resume controls for separate review. `pg_dump -Fc` can snapshot the database with writers running; whole-system consistency with mutable artifacts/sessions is not yet demonstrated. No pause is justified or authorized from empty connection metadata alone.

## Verification and rollback status

This update uses the public-key/tool inventory and local free-space inspection only; no broad test suite repeated. Prior synthetic restore tests remain synthetic evidence. No actual production backup, off-host transfer, custodian decryption, independent production-data restoration or rollback is certified. Abort execution until prerequisites and explicit operation approval exist. Production remains backend v8.6.0 / frontend v8.7 with previous services, authentication and routing unchanged. No rollback action is needed for this read-only preparation.
