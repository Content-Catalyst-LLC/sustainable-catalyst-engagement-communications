# Issue #15 — v12.2 operational checkpoint, 2026-10-28

## Latest continuation — 2026-10-28 (supersedes the paused checkpoint below)

The bootstrap failure is corrected **only on review branch** `codex/issue15-postgres-bootstrap-fix`, source `d16bf44202de38db90aebdd29283b88febb71d1b`, draft PR #22. Owner-selected merged main baf31877 remains unchanged and still has the original bug. No automatic merge or production deployment.

- Fixed initial migration now selects its original 13 tables, excluding later audit metadata. Two new tests compile the actual migration chain. No table drop, schema-head change or downgrade bypass.
- **1038 tests passed on both Mac Python 3.11 and isolated Contabo Python 3.12**, one inherited deprecation warning each.
- Real synthetic PostgreSQL 16: fresh upgrade to 850_001, repeat no-op upgrade, create/read, duplicate conflict, viewer-write denial, cross-tenant read/header/payload denials, pg_dump/pg_restore matching fixture rows, and destructive-downgrade refusal passed. Owned container/network removed; generated credential file deleted. Production backup/restoration and human OIDC were NOT tested by this rehearsal.
- Exact corrected source hashes independently matched across hosts. ZIP and all members verified: `scec-v12.2-issue15-d16bf442.zip`, SHA256 `9a04a2ce657adaefd786b17788006cbbe94ebd6731d79ae5118e46a10ef30b79`. See `migration-fix-certification.json` and `migration-fix-contabo-postgres.json`.
- Only protected file intentionally changed is `backend/alembic/versions/820_001_initial.py`; other protected files remain identical. Do not claim all original protected files unchanged for this correction.
- New staging checkout `/home/catalystadmin/scec-v122016/repository` is clean detached d16bf44, with its own backend/.venv. Evidence/logs and synthetic dump are in its parent. No test server remains. Prior baf staging directory remains preserved. Do not rerun the staging creator into an existing directory.
- Read-only production recheck: vmi3544820, backend v8.6.0 SHA 280c6b9516f9a9cafca0682f7656964077367d7d, frontend image sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652, same Caddy hash d967dbb094a392cdf8f94e17881f2b3ac029f3c4e3295bc7d84d6fcaeb296f2b. Production unchanged.
- Added `DEPLOYMENT-PLAN-v12.2.md` and `BACKUP-ROLLBACK-PLAN-v12.2.md`: version-pinned installation forms, phases, approval boundaries, recovery scope, non-disruptive consistency decision, encryption/restore checks, abort/resume and rollback requirements. They explicitly identify missing DB/store/writer mapping and unreviewed forward/inverse proxy diff; no false executable cutover or safe pause command is claimed. Production execution remains prohibited without scoped approval.

All seven production gates remain unsatisfied. The persistence gate now has **partial isolated evidence on the corrected branch**, but still needs existing-schema compatibility, approved production store/backup scope, independent backup/restore and rollback evidence, and other applicable persistence/transaction checks. Human OIDC/two-organization authorization, session bridge/CSRF integration, operational privacy approval, launcher/Release Console mapping and HTTPS operational checks remain open. No production approval is requested while gates are open.

Next work: review PR #22 compatibility and select an approved future source after review; resolve restricted configuration/DB/store/writer metadata through an authorized administrator; verify Release Console mapping and Feedback launcher correction proposal; obtain owner review of privacy/operator schedule and proposed isolated OIDC identities; turn backup/rollback placeholders into exact reviewed commands only once their missing prerequisites are established. Do not repeat completed regression unless source changes. New staging operator is `work/scec/issue15/stage_migration_fix.py`; portable PostgreSQL verifier is committed under tools on d16bf44 and takes explicit root/SHA/image ID. Scope is isolated staging only.


**NOT PRODUCTION CERTIFIED. Feature development paused. No merge, deployment, production writes, restart, writer pause or new capability activation.** Owner requested a low-usage preservation stop.

Operational target: merged main `baf31877c01e525b610a87830bb0165376ab16e3`. Fresh pinned installations: Python 3.11 Mac **1036 passed**, Python 3.12 isolated Contabo **1036 passed**, one inherited deprecation warning each. Source preflight PASS; owned temporary loopback process stopped and port released. Every one of 253 tracked source hashes matched across hosts. Original 16 protected files unchanged. Historic checksum differs on three comment-only Python files and omits new Docker ignore file; fresh external manifest and byte-verified Git archive saved. Initial Python 3.14 installation failed due to pinned native dependency support; it is not a supported execution result.

Live Contabo hostname `vmi3544820`: latest backend health **v8.6.0**, clean checkout `280c6b9516f9a9cafca0682f7656964077367d7d`; older units also running. Static frontend **v8.7**, checkout `35b5ac363fdebd471f94d8092e943722bc7267e3`, immutable image `sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652`. Container HTML/nginx bytes match that checkout. Public hostname `engagement.sustainablecatalyst.com` serves the static shell; API path returns HTML, not a verified backend API. No running v12.2 deployment found. Bound service identity and persistence=0 observed; no human OIDC environment found in running process. Protected environment files are unreadable to audit account, so file contents remain unverified.

Homepage Release Console says Contact and Engagement v2.0.2 / short SHA 3f24697; product/repository/runtime mapping remains unresolved, so this cannot attest SCEC deployment. Valid public DNS/TLS observed. Four protected WordPress destinations retained requested URLs; `/feedback/` redirected to an unrelated article. No forms submitted or pages changed.

## New blocking failure

Real synthetic-only PostgreSQL 16 fresh migration failed at `830_001_audit.py:13`: **DuplicateTable: engagement_audit_log already exists**. No fixture CRUD, backup/restore or database rollback certification passed. Investigate initial migration importing mutable current metadata before later audit migration. Do not edit historical migrations casually or certify modified source as baf31877. All owned test containers/networks and temporary secret files removed. Production database/configuration never copied.

## Seven gates

| Gate | Actual status |
|---|---|
| HTTPS/DNS/TLS | Partial; renewal, redirects and approved header/proxy policy incomplete. |
| WordPress launcher | Not satisfied; Feedback mismatch and no verified candidate integration. |
| Human session | Blocked; issuer/client and authorized two-organization identities missing; session cookies not wired to API Bearer dependency. |
| CSRF/revocation/expiry | Source/unit evidence only; live browser acceptance blocked. |
| Live tenant isolation/roles | Blocked; no authorized human set; real DB migration failed. |
| Privacy/retention | **NOT SATISFIED**, owner confirmed; draft periods/operator/rights/unsubscribe/enforcement not approved. |
| Persistence/backup/restore | **NOT SATISFIED**; fresh migration failure; coordinated production backup and independent restore/rollback outstanding. |

279-route source/dependency inventory saved. Security review records no global body-byte/rate protection found, legacy authorization bypass risk outside bound mode, persistent legacy write handlers behind flags, and static frontend CSP/proxy integration gaps. These require narrow reviewed remediations, not feature activation.

Owner-review drafts: `SCEC-OPERATIONAL-PRIVACY-RETENTION-DRAFT.md` and `OIDC-NONPRODUCTION-PROPOSAL.md`. No policy approval, privacy operator appointment, issuer deployment or synthetic identity authorization is implied. Do not use production accounts or credentials in staging.

Next session: address migration blocker on a narrow review branch; finish exact version-pinned deployment, coordinated encrypted backup, independent restore, abort/resumption and rollback procedures; resolve launcher/Release Console mapping; obtain sanitized administrator configuration evidence; review privacy schedule; propose isolated issuer/two-organization tests. Preserve existing systemd/venv backend and Docker static frontend architecture. Do not run candidate Compose against the live container name/port. No production backup or cutover was executed. Destructive migration downgrade is forbidden by source; restore-based rollback must be verified.

Full private operator handoff, raw logs, source manifest and archive are saved locally in `outputs/SCEC/Issue-15`; they are not all published to GitHub. Production go/no-go remains unavailable while mandatory gates are open. Later roadmap development remains paused.
