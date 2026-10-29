# SCEC remaining production build map

2026-10-28. Operating record: GitHub Issue #15. **Overall production release NO-GO.** Current production remains backend v8.6.0 / frontend v8.7. No production data, privileges, service or deployment configuration changed during reconciliation.

Approved v12.2 source: **381a5a382c9b613136c091d0c1f235f36907c037**, including merged PR #22. Complete tree equals tested **d16bf44202de38db90aebdd29283b88febb71d1b**. Full regression 1,038 passed on Mac and Contabo was not repeated for this identical tree. Draft PR #21 holds documentation/evidence; draft PR #23 proposes only the inactive-public-API fail-closed correction. A source merge, staged test or policy appointment is not production activation approval.

| Package | Scoped decision | Critical dependency / blocker |
|---|---|---|
| SCEC-R01 Schema reconciliation | **GO to preserve DB unchanged; NO-GO for corrective DDL or cutover** | Observed mismatch explained and isolated; security/data/recovery remain separate |
| SCEC-R02 Backup and rollback | **NO-GO** | Approved encryption recipient/custodians, off-host destination, complete writer/store scope and actual production restore/rollback evidence |
| SCEC-R03 OIDC/tenant security | **NO-GO** | Verified isolated issuer/client/identities, session/principal integration and real acceptance |
| SCEC-R04 Operational privacy | **NO-GO** | Policy/procedures unapproved; independent controls and actual workflows unverified |
| SCEC-R05 Public routing/WordPress | **NO-GO** | PR #23 review, authenticated routing, actual Feedback destination and site backup/acceptance |
| SCEC-R06 Release Console | **NO-GO** | Verified registry mapping and approved actual-runtime integration, not a GitHub tag badge |
| SCEC-R07 Production deployment | **NO-GO** | R02–R06 and seven mandatory gates, exact approved cutover/inverse diff and owner approval |
| SCEC-R08 Phased activation | **NO-GO** | Verified deployed identity plus separately approved capability gates and operational handover |

## SCEC-R01 — Database schema reconciliation

**Sources/work:** production checkout `280c6b9516f9a9cafca0682f7656964077367d7d`; target `381a5a382c9b613136c091d0c1f235f36907c037`; tested tree `d16bf44202de38db90aebdd29283b88febb71d1b`. Retrieved restricted administrator report; independently reproduced its comparison; checked source migration/model hashes and runtime service metadata.

**Tests/evidence:** `SCEC-R01-FINDINGS.md`, exact `schema-structural-differences.json`, private administrator report, `migration-source-lineage-comparison.json`, seven focused comparer tests, `check-cast-equivalence.json`. 18 tables / 159 column descriptors / 70 indexes match; constraint names and RLS flags match; 49 of 68 constraint definitions match exactly. Remaining 19 CHECK differences are element-wise versus array-level VARCHAR-to-TEXT casts. All 380 isolated cases matched. Both running versions are 16.15. Recreating production definitions in isolation yielded the synthetic fingerprint; original production hash remains distinct and preserved. No silent normalization.

**Dependencies/resolution:** observed table-schema discrepancy reconciled within exported scope. Production head 850_001 matches target head; later migration/model source bytes match, bootstrap differs only by reviewed repair. No schema repair indicated. Historical execution provenance, data validity, full external writer inventory, recovery and broader security remain unverified.

**Impact/rollback:** production reads only. Synthetic restoration/DDL/evaluation ran only in owned isolated containers, now removed. No production rollback needed for this work. Preserve main and eight additional databases. Do not rerun/stamp production migrations or drop/recreate CHECKs to force hash equality.

**Decision:** **GO for unchanged-schema preservation; NO-GO for production DDL or deployment.**

## SCEC-R02 — Coordinated backup and rollback certification

**Source/work:** target `381a5a382c9b613136c091d0c1f235f36907c037`; current production backend `280c6b9516f9a9cafca0682f7656964077367d7d`; frontend `35b5ac363fdebd471f94d8092e943722bc7267e3` / immutable image `sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652`. Backup/rollback proposal prepared. Main DB and eight historical candidates identified from administrator metadata; all preserved. GPG is installed; no new encryption dependency required.

**Tests/evidence:** corrected synthetic PostgreSQL dump/restore, fixture equality, destructive downgrade refusal and independent fresh-container restore passed. These are not production-backup tests. Actual production encrypted backup, off-host transfer/decryption, independent restoration, RPO/RTO and rollback rehearsal have **not** passed.

**Dependencies/blockers:** approved public encryption key/fingerprint, off-host destination, recovery custodians, preservation classification, writer/store/WordPress boundaries and operator execution access. Current app flags/absent DSNs and empty sessions do not exclude administrative/external writes. A standalone pg_dump snapshot is consistent without pausing writers, but cross-store guarantees require mapped checkpoints/versioning or separately approved quiescence. No safe pause is inferred or executed.

**Impact/rollback:** preparation only. Later approved backup must encrypt restricted auth/proxy/runtime material, avoid shared live PostgreSQL filesystem copies, preserve the existing image/source, and restore only to isolation. Current and unrelated services remain running. Exact inverse proxy patch cannot exist until the forward integration is reviewed. No production restore or destructive downgrade.

**Decision:** **NO-GO** until production backup and independent recovery are certified. Next: obtain missing encryption/off-host/custody choices, finalize concrete scoped procedure and verify writer/store boundaries before execution.

## SCEC-R03 — OIDC authentication and tenant-security acceptance

**Source/work:** human-auth/service-principal modules at `381a5a382c9b613136c091d0c1f235f36907c037`. Existing issuer/config inspection and isolated-provider proposal prepared. No verified production OIDC issuer or human-session configuration identified.

**Tests/evidence:** source regression and synthetic PostgreSQL service-principal tenant/header/payload/role denials passed on tested tree. They do not prove human OIDC, real cookie/proxy/CSRF behavior, session revocation or production tenant security.

**Dependencies/blockers:** establish reviewed isolated provider/client/two synthetic organizations and authorized distinct identities; no production accounts/credentials copied. Implement/review session-to-principal boundary preserving roles, tenant and CSRF; current API dependencies accept service Bearer tokens, not a human cookie by itself. Verify scopes, mapping, expiry/revocation/logout, role matrix, tenant negatives, request limits and least-privileged DB role before any persistence exposure. OS user catalystadmin and DB owner are not observed application PostgreSQL identities; no runtime DSN found.

**Impact/rollback:** isolated testing only until accepted. No production identity changes or registration replacement. Retain existing auth files/keys and current bound-service behavior. Any eventual identity/proxy change needs a tested inverse and separate approval.

**Decision:** **NO-GO**. Next safe work: configure the isolated experiment and tests from the existing preferred architecture after its concrete inputs/resources are verified; no claim that a proposal is a working IdP.

## SCEC-R04 — Operational privacy, consent, retention and unsubscribe

**Source/work:** privacy source at `381a5a382c9b613136c091d0c1f235f36907c037`; revised schedule, matrix and procedural supplement in PR #21. Business owner confirmed as both primary and designated deputy: **one individual**, no independent alternate. Independence/separation-of-duties controls remain unsatisfied where required.

**Tests/evidence:** synthetic privacy classification/guard tests are part of recorded source regression. Actual notice/basis decisions, operational rights intake, withdrawal/unsubscribe/suppression, backup lifecycle and restore-time reconciliation are not certified. No repeated broad suite for policy-document edits.

**Dependencies/blockers:** final controller/purpose/basis/processor/location/WordPress register; approved deadlines, notice and workflow; approved 90/180/180/90/365-day proposal, 30-day backup and 365-day audit proposal. All periods remain unapproved. Independent review/coverage and technical custodians must be assigned where required; one person cannot self-approve an independent control.

**Impact/rollback:** documents only. No live collection/persistence, subscriptions, outbound, retention enforcement or deletion enabled. Future policy publication and enforcement need separate approvals and rollback/hold/suppression reconciliation behavior.

**Decision:** **NO-GO**; production privacy acceptance NOT SATISFIED.

## SCEC-R05 — Public API routing and WordPress integration

**Sources/work:** baseline `381a5a382c9b613136c091d0c1f235f36907c037`; proposed routing `0d565362238ef092ff823ddd942ae984d8956cd5`, draft PR #23. Public metadata checked without submissions. Current API-shaped URLs return static HTML 200. Proposed interim correction returns JSON 503 until activation.

**Tests/evidence:** exact candidate nginx configuration passed isolated syntax, unchanged root HTML hash, healthz, JSON 503 at `/v1`, `/v1/contracts/canonical` and `/v1/human-auth/login` and preserved CSP. Owned container/network removed. Four published page slugs verified; feedback slug absent and URL redirects to an unrelated article. No page created, replaced or redirected by this work.

**Dependencies/blockers:** review patch; R02 backup; R03 browser/API integration; authenticated WordPress administrator verification of actual existing Feedback destination and bridge mapping. Do not substitute an invented route or treat 503 as completed authenticated integration. Preserve Contact, Feedback, Feature Suggestions, Channel and Support.

**Impact/rollback:** production untouched. Any approved route/page/plugin adjustment must have a narrow versioned diff and site-specific backup/inverse. Do not run colliding frontend Compose or restore the whole proxy over another project's changes.

**Decision:** **NO-GO** for production integration/activation; interim patch remains review-only.

## SCEC-R06 — Homepage Release Console integration

**Sources/work:** SCEC target `381a5a382c9b613136c091d0c1f235f36907c037`; inspected Product Support & Feedback source `d454431946d1b376c9b37af89bd1b9d87efea4d2` contains registry/release-board interfaces. This inspected source is not attestation of all live plugin bytes. Live Contact and Engagement v2.0.2 github-tag row is not SCEC runtime evidence.

**Tests/evidence:** public HTML/JS inspected; source shows protected registry administration and legacy plugin product mapping. No authenticated registry/runtime integration or homepage write performed.

**Dependencies/blockers:** verify live mapping; preserve legacy plugin row; review a distinct SCEC runtime record with actual backend/frontend/source/image, capability flags, observation timestamp and stale/unavailable state. Separate available GitHub release from deployed version. Do not display v12.2 as running until R07 live evidence proves it. Requires site backup/admin authorization and approved narrow adapter/renderer changes.

**Impact/rollback:** no current homepage changes. Future approved changes need saved registry/options/plugin state and an exact inverse, preserving existing products and destinations. No credentials/private records in public telemetry.

**Decision:** **NO-GO** until actual runtime integration and homepage acceptance are verified.

## SCEC-R07 — Version-pinned production deployment and verification

**Source/work:** immutable merged target `381a5a382c9b613136c091d0c1f235f36907c037`; verified archive/manifest in `merged-release-manifest.json`. Source tree equality reuses executed d16bf44 regression; no redundant full suite. Deployment proposal preserves existing systemd/venv + static Docker architecture. No v12.2 production unit, cutover or migration executed.

**Tests/evidence:** source regression, synthetic recovery and isolated routing evidence above; no new live deployment evidence. Current production is v8.6.0 backend / v8.7 frontend, not v12.2. Deployment timestamp for v12.2 is **none**.

**Dependencies/blockers:** R02–R06, all seven live gates and exact owner-approved source/profile/port/forward-and-inverse-proxy diff, backup and rollback evidence. Retain DB unchanged; no automatic Alembic startup or production schema rewrite. Any separately accepted routing patch must be included in a newly pinned/reviewed candidate rather than silently relabeling the baseline.

**Impact/rollback:** future approved side-by-side SCEC-only process and narrow routing change; leave old units/image intact. No unrelated restarts. Verify public service/content type/source/version/auth/tenant behavior before accepting cutover, with immediate scoped inverse on failure. No production cutover approval requested while gates remain open.

**Decision:** **NO-GO**.

## SCEC-R08 — Phased activation and operational closure

**Source/work:** target `381a5a382c9b613136c091d0c1f235f36907c037` plus only separately accepted, pinned fixes. No capabilities newly activated.

**Tests/evidence:** no live phased activation has run. Staging synthetic discovery/newsroom behavior is not publication permission or operational certification. Final live system version, security acceptance, approved capabilities and homepage record do not yet agree at v12.2.

**Dependencies/blockers:** R01–R07 accepted within their scope and separate owner-approved capability/profile list. Begin only with approved authenticated read-only discovery/newsroom. Real subscriptions, outbound communications, production writes, automatic deletion and federation retain their own additional gates and explicit authorization. Record monitoring/abort thresholds, operator coverage, independent controls, incident ownership and executed rollback.

**Impact/rollback:** future individually approved flags/routes only; record original settings and inverse per phase. Stop affected activation on any recovery/identity/tenant/privacy/security failure while continuing independent safe preparation. No broad enable-all switch.

**Decision:** **NO-GO** for activation or milestone closure.

## Preserved later work

Keep verified source commits v12.3 `8a58c703ac5d9d48373e90aada75f891c71074cd`, v12.4 `ba9cd9da07f5ef98ebcbe82d9072fd2213a3d126`, and v12.5 `1143a3f24f6239109701fc8f1e6b8d6da1b1a8af` intact for subsequent normal review/integration/testing **after production recovery**. Historical test evidence remains distinct from main integration and production certification. No v12.6 or v13 development. Existing local v12.6 WIP remains paused/preserved, not certified.
