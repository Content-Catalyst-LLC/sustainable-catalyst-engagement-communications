> Technical execution update: see [SCEC-R02-TECHNICAL-RESULTS.md](SCEC-R02-TECHNICAL-RESULTS.md). Prior planning/test-status statements below are historical; primary custody is confirmed and closed. No additional owner-review package is requested.

# SCEC-R02 — Next owner-review package

2026-10-28. **NO-GO; documentation only.** Business owner explicitly accepted Primary Recovery-Key Custodian appointment. This is not secure-storage verification or authority to generate/import a key, run backups, transfer production data, pause writers or deploy.

Read the [provisioning procedure and decision matrix](SCEC-R02-OWNER-DECISION-MATRIX.md) together with the [capacity evidence](destination-capacity.json). The following selections remain open:

| Review item | Required owner decision/evidence | Current status |
|---|---|---|
| Primary custody | Business owner appointment | CONFIRMED; secure storage still unverified. |
| Independent verification | Name a distinct verifier; obtain acceptance and document independence, fingerprint verification channel and witnessed synthetic recovery evidence | NOT APPOINTED. Same-person privacy primary/deputy roles do not count as independent reviewers. |
| Alternate custody | Name alternate; obtain acceptance; approve contingency access and separately protected recovery media | NOT APPOINTED. |
| Backup operator | Identify authorized operator and obtain formal acceptance; distinguish operator access from private-key custody | PENDING formal acceptance. |
| Provisioning environment | Approve offline workstation, encrypted key/revocation storage, recovery-media locations, access log and compromise response | PENDING; provide identifiers/attestations only, never keys/passphrases in chat or Git. |
| Key profile | Review proposed dedicated RSA-4096 primary/encryption subkey, UID, one-year expiry and renewal plan after compatibility check | PROPOSED; no key generated or creation authorized. |
| Off-host primary storage | Identify exact existing independently administered endpoint/device, responsible operator, jurisdiction, capacity, costs and recovery access | NOT APPROVED; no verified primary endpoint. |
| Secondary storage | Select exact approved Mac/media location; verify encryption, ownership, health, physical separation and custody | NOT APPROVED. Prior free-space readings are snapshots, not sufficient security/capacity evidence. |
| Capacity | Measure complete recovery-set size B and destination free space F; initially require 34B <= 0.8F, increased for growth/larger restore workspace | PENDING complete scope/size; do not create a production dump merely to measure under this instruction. |
| Retention/objectives | Review proposed daily encrypted sets, 30-day rolling retention, RPO <=24h and RTO <=4h | PENDING formal privacy/recovery approval and timed verification. No expiration/deletion job authorized. |

Approval sequence: (1) resolve appointments, storage and key profile; (2) separately approve exact key-provisioning/public-import and synthetic recovery operations; (3) witness key recovery and finalize production scope/consistency, fixed-path backup/transfer and isolated-restore commands; (4) obtain separate exact-operation approval before any production backup or transfer; (5) independently verify recovery before requesting deployment approval. No blanket approval or control bypass is implied.

Backup scope must still reconcile artifact/session stores, all SCEC writers, restricted authentication/proxy recovery and historical database classification. Preserve current database and all historical databases; no DDL or grant changes. Reuse existing synthetic test evidence without presenting it as production restoration. Future rollback must retain old source/image/data, use a reviewed reversible SCEC-only proxy change, and never overwrite production databases or restart unrelated services.

Verification for this appointment update: documentation consistency and Git whitespace checks only. No cryptographic, production recovery or application test was newly executed. Production remains unchanged.
