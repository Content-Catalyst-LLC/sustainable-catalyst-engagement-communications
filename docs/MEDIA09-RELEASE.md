# Privacy-controls implementation update

See [privacy operations](MEDIA09-PRIVACY-OPERATIONS.md) and [clean notice verification](MEDIA09-NOTICE-VERIFICATION.md) for the implemented, default-disabled retention/rights/erasure/restore controls and current approval requirements. The earlier release checkpoint below predates this increment.

# Media / Press release candidate — 2026-11-13

The candidate extends existing PR #37 and merges the existing Media-08 WordPress/Press implementation into it. It uses the canonical Media Contact/Inquiry PostgreSQL tables, existing platform OIDC sessions, and the existing WordPress Press Room. No production activation, DNS, newsletter sending, or Research publication change has occurred.

## Working implementation

- `/press/`: responsive Press/contact page with four inquiry categories, accessible validation, privacy notice, honeypot, signed form token, same-origin submission and receipt/error handling. No browser service credentials.
- `/press/inquiries`: first-party create with tenant-wide PostgreSQL transaction lock, replay protection, contact deduplication by normalized email, five new inquiries/minute and atomic canonical/detail/audit writes.
- `/press/inbox` and `/press/staff/inquiries`: platform OIDC session only; membership and tenant rechecked per request, CSRF for writes, bounded list/detail, assignment to current same-tenant staff, versioned review/close (admin close). Default-off when identity is unconfigured. No WordPress user login authority.
- Existing WordPress `[sc_press_room]` retains approved-release archive and can link the hosted first-party form through `SCEC_MEDIA09_PRESS_URL` (HTTPS, Sustainable Catalyst host allowlist). `[sc_press_inquiry]` provides the same link elsewhere. No contact records or tokens are stored in WordPress.
- Optional `backend/app/hubspot.py`: backend contact/company allowlist, email/domain lookup before write, ambiguous-match refusal, safe classified outcomes and manual retries. Explicit admin-approved contact export stores provider outcome in the existing inquiry detail. Company connector tested against a mock; no external organization audience/import or company export UI is enabled. No newsletter, research, deals or tasks mapping.

## Staging and acceptance

Private Contabo service: `sc-media09-staging.service` (user systemd), loopback HTTPS port **18982**. SSH tunnel: `ssh -N -L 18982:127.0.0.1:18982 catalystadmin@94.72.113.77`, then `https://localhost:18982/press/`. Seven-day self-signed certificate is for this private staging preview only. Browser acceptance is pending certificate trust; do not disable production TLS validation.

Dedicated PostgreSQL 16 acceptance container/network/volume are synthetic fixtures, isolated from existing Media production data. No production database/config was copied. Actual acceptance exercised migration, concurrent replay, contact deduplication, atomic writes, tenant/auth/role denials, CAS assignment/close, rate limit, reconnect persistence, forward migration and backup restore into separate disposable databases. Receipts and dumps stay in `/home/catalystadmin/media09-private-20261113/` (protected directory). They do not certify production backups or real-account login.

Local complete backend suite: **1,133 passing** before final packaging. Repeat against the final source artifact on Contabo with a clean environment, since staging flags contaminate legacy test defaults. PHP lint and existing Media WordPress regressions are required. Do not equate mocks with live HubSpot or synthetic session fixtures with an accepted real identity.

## Real-data configuration (not enabled)

`SCEC_MEDIA09_REAL_INTAKE_ENABLED=1` additionally requires `SCEC_MEDIA09_APPROVED_NOTICE_FILE` pointing at an absolute mode-0600 JSON file outside the checkout. Required nonempty strings: `version`, `text`, `privacy_url` (HTTPS), `privacy_approval_ref`, `security_approval_ref`, `identity_acceptance_ref`, `cutover_authorization_ref`. These references record independently obtained approvals; writing them is not approval. Use the approved full notice (controller, reply purpose/basis, retention, rights contact and processor/transfer information). Existing synthetic mode and reserved-address validation remain the staging default.

Real mode uses the same tables and workflow, marking `synthetic_only=false`; it has no newsletter consent or automatic CRM export. Migration head is `media09_1_003`. The existing human OIDC boundary can use the dedicated Media persistence only in explicit synthetic staging or when the real-release record is configured. Provision an approved HTTPS platform issuer/client, callback `/v1/human-auth/callback`, protected client secret and explicit subject/organization/role mapping. Verify login, MFA policy, expiry, logout/revocation, cross-tenant denial and CSRF with actual authorized staff before cutover. Use a private session-store directory and mode-0600 files. No WordPress identity fallback.

## Optional HubSpot owner action

Provision a **single-account private-distribution static-auth access token** in the existing approved HubSpot account, with only `crm.objects.contacts.read`, `crm.objects.contacts.write`, `crm.objects.companies.read`, `crm.objects.companies.write`; install it as a protected backend file and provide its path. See [HubSpot authentication](https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/overview). Never paste the token into chat, a browser template or GitHub. No account or credential has been provisioned by this release. Owner/account approval includes any provider privacy/cost decision. First-party Media works without it.

Operator activation, after that action and approved export scope: set `SCEC_HUBSPOT_TOKEN_FILE` and `SCEC_MEDIA09_HUBSPOT_ENABLED=1`; an administrator must explicitly approve each reviewing inquiry's current revision. Revoke by setting enabled=0 and revoking/rotating the provider token. Failed/ambiguous sync remains first-party and records no private provider response. A timed-out provider write requires reconciliation; there is no automatic bulk retry/import.

## Production cutover (NOT executed)

1. Obtain owner-approved privacy/controller/basis/retention/rights procedure, security acceptance, real platform identity acceptance, and explicit production cutover authorization. Publish the reviewed privacy URL before opening collection. Confirm rights/deletion procedure covers canonical records, supplemental messages, CRM copies and backup retention. No legal approval is inferred from a technical test.
2. Capture exact current WordPress plugin/page/proxy artifact and a real production PostgreSQL backup. Restore that backup in isolation and verify it. Preserve existing service and proxy targets. Synthetic fixture restores do not satisfy this step.
3. Deploy the exact reviewed artifact with real collection off. Apply additive migrations against the approved existing Media database in a maintenance window after backup. Configure HTTPS routing for the hosted form/inbox/API, approved OIDC origin/callback, and protected notice/session/credential paths; keep all newsletter/research/send flags unchanged.
4. Verify `/health`, `/press/health`, `/press/`, all assets, signed-out inbox denial, approved-login session/CSRF/tenant tests, synthetic inquiry receipt/replay/review/assignment and storage health against the actual public routing. Verify WordPress Press archive and link. Confirm no raw body/credential/query logging. Enable real intake only for the separately authorized cutover.
5. Roll back immediately for health/auth/privacy/abuse failures: disable real intake and optional HubSpot first, restore previous proxy/plugin/service target and stop only the new owned service. Preserve inquiries received after cutover for controlled reconciliation. Schema is additive; do not run destructive downgrade or overwrite live data with an older backup. Backup restore requires a separately approved recovery window and data reconciliation.

## Remaining release blockers

Approved privacy/security/cutover record and public policy; accepted HTTPS platform client and staff provisioning; production host/proxy/WordPress installation and verified production backup/restore; browser acceptance with trusted staging/public TLS. Live HubSpot token/account action is optional. This is a tested release candidate, not a released production product.
