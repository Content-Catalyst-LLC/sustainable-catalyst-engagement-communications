# Issue #15 — v12.2 operational checkpoint, 2026-10-28

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
