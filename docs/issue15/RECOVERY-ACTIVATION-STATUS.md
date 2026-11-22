# Recovery and activation status — 2026-10-28

**Production recovery/activation milestone NOT COMPLETE. No production mutation or cutover.**

| Required field | Recorded state |
|---|---|
| Production hostname | `vmi3544820`; public `engagement.sustainablecatalyst.com` |
| Production backend | `scec-v860.service`, health v8.6.0; checkout `280c6b9516f9a9cafca0682f7656964077367d7d` |
| Production frontend | `scec-engagement-web-v870`, v8.7 source `35b5ac363fdebd471f94d8092e943722bc7267e3`; image `sha256:04e8fe6b7cc4701fb4cba71cb6a2891fa095dc54df17dd6a7bfbc7012f199652` |
| Corrected merged v12.2 target | PR #22 merged under explicit owner authorization: `381a5a382c9b613136c091d0c1f235f36907c037`; tree identical to tested `d16bf44202de38db90aebdd29283b88febb71d1b` |
| Main production database | Administrator reports host PostgreSQL `scec_engagement_v820`, revision `850_001`, 18 tables; raw schema reconciliation pending |
| Other databases | Eight additional SCEC databases reported; preserve all pending names/ownership/recovery classification |
| Deployment timestamp | No v12.2 deployment occurred; original production deployment timestamp not verified |
| Enabled capabilities | Existing static read-only shell and bound loopback service contracts; no new v12.2 capability activated. Persistence observed disabled; no verified human OIDC/session config |
| Completed acceptance gates | **None of seven fully satisfied.** Source regression and synthetic recovery are supporting evidence only |
| Backup/rollback evidence | Synthetic PostgreSQL dump/restore, tenant/role negatives and destructive downgrade refusal passed on corrected source; fixture also restored independently into a fresh isolated container. Production backup/decryption/off-host recovery/rollback remain unverified |
| Privacy accountability | Primary and designated deputy are the same confirmed business owner. Independent alternate unappointed; independent approval/separation of duties not satisfied where required. Operational policy remains unapproved; privacy gate NOT SATISFIED |
| Public routing | Draft PR #23 returns JSON 503 for inactive /v1 paths; focused owned-container test passed, production unchanged. This is not authenticated API integration |
| WordPress | Four published pages verified. No published `feedback` slug found; /feedback/ redirects to an unrelated article. No destination substituted or page changed |
| Release Console | Inspected source in renamed Product Support & Feedback repository at `d454431946d1b376c9b37af89bd1b9d87efea4d2` labels `contact-engagement` as WordPress plugin `sustainable-catalyst-contact-engagement`; exact live registry configuration is not yet attested. Live v2.0.2 github-tag row is not runtime attestation for SCEC; authenticated mapping review pending |

## Privacy decision record

Confirmed owner assignments are one person, not two independent reviewers. No self-approval satisfies a required independent control. No policy period, live procedure or activation is approved by these assignments. Proposed 90/180/180/90/365-day source periods, 30-day backup period and 365-day audit period remain under review. Revised draft, approval matrix and supplement cover purpose register, receipt clock/extensions, rights intake/deadline assessment/escalation, optional consent, withdrawal/unsubscribe/suppression, backup expiration/reconciliation, processors/jurisdictions/WordPress flows and missing independent/technical custodians.

## Exact next prerequisites

1. Administrator reviews/runs `sudo python3 /home/catalystadmin/scec-issue15-recovery-metadata/admin-schema-and-writers.py` and returns its sanitized JSON. It only reads schema/catalog/privilege/job metadata. Compare its schema to the corrected synthetic fingerprint `38f1a9fa093e72785551064e5749a7d8e3b819c5b97da3073524e6b56ee97704`. A mismatch requires a table/column/constraint/index assessment, not a blind migration. Empty connection metadata is not inactivity proof.
2. Map all candidate writers/service dependencies, artifact/session references, owner/admin write paths and database ownership; preserve historical databases and backups. Establish exact backup destination, encryption/key custodians, off-host copy and authorized recovery scope. No production data or configuration changes during reconciliation. Backup permissions do not authorize writer pauses or unrelated service changes.
3. Complete coordinated production backup and independent restoration/rollback evidence only after scope and privileges are established. Current runbooks deliberately retain missing writer-control/proxy-diff prerequisites rather than invent safe commands.
4. Obtain approved existing Feedback destination/WordPress mapping and authenticated release-registry mapping. Keep all five intended destinations preserved. Add a distinct SCEC runtime record using actual service/source/image/capability observations and checked timestamp, preserving the legacy plugin row; no manual v12.2-current claim before deployment.
5. Establish authorized isolated OIDC/client/two-organization identities and session-to-principal/CSRF/proxy integration. No production account import. Complete privacy policy and independent controls; execute live gate evidence. Outbound/subscriptions/persistence/deletion/federation remain disabled.
6. Only after safeguards, all mandatory gates and scoped owner approval: execute immutable version-pinned deployment, verify public runtime identity and rollback, then separately approve incremental read-only discovery/newsroom capabilities. No v12.3/v13 feature work.

## Evidence limits

Owner-provided administrator inventory is recorded as such; raw file hash values, eight database names and schema details were not supplied in chat. No absence of data, writers or historical responsibilities is inferred. No real SSO, WordPress data-flow or retention/unsubscribe process is certified. The same-person appointment cannot close independence requirements. All production gates remain open.
