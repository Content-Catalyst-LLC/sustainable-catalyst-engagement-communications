# MEDIA-07.3 — Synthetic-only listmonk draft connector handoff

**Status, 9 November 2026:** Python implementation and mocked CI acceptance on [draft PR #34](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/pull/34); **not deployed as an authenticated Python API on Contabo, and not connected to Bluehost Newsletter Studio**. The separate listmonk/PostgreSQL/Mailpit containers are already running in isolated Contabo staging, with the Nov 9 operator receipt reporting PASS. Do not rerun the first-time listmonk installer.

**Deliberate scope:** Create/reconcile synthetic **listmonk campaign drafts only**, not subscriptions, email sending, scheduling, status transitions, release approvals, external publishing, or real-audience campaign management.

## Implemented API and gate

Module: `backend/app/media07_listmonk_draft_v1280.py`, included in `app.main` behind the existing `require_service_token` dependency.

- `GET /v1/newsletter-studio/listmonk/status` — authenticated configuration status, **not** a provider health claim.
- `POST /v1/newsletter-studio/listmonk/drafts` — require bound `administrator` service principal, matching organization header/token/body, allowlisted **single organization**, existing MEDIA-07 staging flag, and an additional default-off draft-sync flag. Writes a *draft only* via listmonk's `POST /api/campaigns`.
- `POST /v1/newsletter-studio/listmonk/send|schedule|test-send|subscribers/import` — always 503; no underlying provider calls.
- `POST /v1/newsletter-studio/listmonk/campaigns/{id}/status` — always 503; all other status-write methods remain absent.
- No reader or editor can supply list IDs, recipients, provider URLs, schedules, sender passwords or API keys.
- Input includes `organization_id`, `newsletter_ref` (e.g., `wp-newsletter:12`), source-attested `studio_revision_sha256`, **actual rendered HTML fingerprint**, subject, title, plain-text alternative and required `synthetic_only=true`. The service recomputes HTML SHA-256 and rejects mismatches, template directives, active HTML elements and unrecognized fields. **A client-provided source revision is not an independently verified human approval.**
- Only `http://127.0.0.1:18898` is accepted as listmonk origin, using `httpx` with proxies and redirects disabled.
- Credentials are loaded at request time from a separate regular file readable by the service user with **mode 0600** and at most 4 KiB. Never store them in GitHub, WordPress JS/PHP or API responses.
- Server-configured list ID must point to a list with **exact name** `SCEC MEDIA07 STAGING EMPTY`, **private**, **active**, and **subscriber_count=0** verified through `GET /api/lists/{id}` on each request.
- Candidate name is deterministic and source-bound. Before creating, the adapter queries existing campaigns and verifies that a matching draft has exactly the same subject, HTML, plain-text body, content type, messenger and list ID. A changed or non-draft campaign is refused.
- API never invokes `/api/campaigns/{id}/status`, `/test`, `/archive`, send, subscribe or delete. No automatic retry on network uncertainty.

## Environment config for a *separately authorized* Python staging service

These settings must be provided only to the **separate MEDIA-07.3 backend canary**, not to the listmonk Docker Compose env or production MEDIA-05/06:

```dotenv
SCEC_ENV=staging
SCEC_IDENTITY_MODE=bound
SCEC_MEDIA07_STAGING_ENABLED=1
SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED=1
SCEC_ALLOWED_ORGANIZATION_IDS=<exact single staging organization UUID>
SCEC_MEDIA07_DRAFT_ORGANIZATION_ID=<same UUID>
SCEC_MEDIA07_EMPTY_LIST_ID=<ID of newly created private empty list>
SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE=/home/catalystadmin/media07-private/listmonk-draft-credential.json
```

The existing `SCEC_IDENTITY_SIGNING_KEY` must be supplied through the authorized service secret channel (not GitHub or chat). `scope()` also rejects any danger flags. **No deployment script in this PR sets these flags on the current running backend**, and nothing is exposed by public Caddy.

## Operator provisioning — prerequisites, not performed

1. Connect to listmonk through the existing Mac SSH tunnel, `http://127.0.0.1:18898`. In the listmonk UI create a **new private, active, zero-subscriber list** with the exact name `SCEC MEDIA07 STAGING EMPTY`. Record only its numeric list ID. Do **not** select/import the existing Default or real audience list.
2. Under Admin → Users create a dedicated API user/token with the minimum capabilities required to **read one synthetic list and create/read campaign drafts**. Independently verify the role has no campaign scheduling/sending/status-transition privileges; if unable to enforce that, stop before enabling the adapter.
3. In a separately authenticated **interactive Contabo SSH session**, use the reviewed on-host helper `python3 ~/media0708-staging-candidate/deploy/media07/provision-draft-credential.py` **after the new branch has been checked out in a separate candidate worktree**. Or create an equivalent file securely by administrator procedure. The helper prompts without echoing the token and writes `/home/catalystadmin/media07-private/listmonk-draft-credential.json` with directory 0700 and file 0600; it never overwrites an existing file. Do not modify the currently deployed `media0708-staging-candidate` checkout in place. Never paste credentials into CI, a browser URL, terminal screenshots, chat or GitHub.
4. Verify the selected private list has **zero subscribers**, restart and backup/restore provenance of the existing staging containers, and the identity/organization signing boundary. Do not rotate or edit MEDIA-06 service keys as a shortcut.
5. Stage the new Python backend separately on host-loopback without altering existing MEDIA-05/06 services or public reverse proxy. Start with all flags disabled, confirm request denial, then enable **only** draft creation with authenticated canary identity. Test one synthetic campaign draft; confirm exact draft status in listmonk and **no message in Mailpit** caused by draft creation. Re-submit the same fixture once to exercise reconciliation, then inspect source and provider record carefully.
6. Record source commit, backend process ID/port, audience list ID (non-sensitive), role review, receipt, synthetic campaign ID, negative sending tests, rollback plan and exact API status. Never mark real Studio UI integrated until authenticated WordPress-to-Engagement source/revision proof passes.

## 9 November 2026 — Operator credential provisioning correction (SUPERADMIN NO-GO)

The operator verified the correct PR #34 source checkout and reported that `provision-draft-credential.py` successfully created the private on-host JSON file after an initial rejected attempt. **The API identity entered at provisioning was assigned listmonk's Super Admin role. Do not activate `SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED` or use this credential for the bridge.** The script checks filename ownership/permissions and token syntax, **not** the API user's role or its actual permissions. This is **credential-file creation only**, NOT accepted listmonk API integration.

Listmonk v6.2 distinguishes `campaigns:manage` (create/update/delete) from `campaigns:send` (start/schedule/pause/resume/cancel). User roles live at **Admin → Users → User roles**; list-specific grants use **List roles**. Official sources: https://listmonk.app/docs/roles-and-permissions/ and https://github.com/knadh/listmonk/releases/tag/v6.2.0 .

**Corrective operator sequence (not yet performed):**

1. In listmonk UI, **revoke/delete the newly provisioned Super Admin API token**, or disable the unused high-privilege API user. **Do not remove the normal human administrator account.** Keep draft integration disabled.
2. Create an exact-name active private **zero-subscriber** test list. Define a custom **user role** that grants **only `campaigns:get` and `campaigns:manage`**, with **`campaigns:send` absent**; exclude `campaigns:manage_all`, `campaigns:get_all`, `lists:get_all`, `lists:manage_all`, `tx:send`, all subscriber import/manage/query, admin/users/settings and public release privileges. `campaigns:manage` also permits updating/deleting campaigns for permitted lists; listmonk cannot express a narrower create-only role here.
3. Define a **list role** with view/read access to **only** this synthetic empty list and assign both roles to a new API service account, e.g. `sc_media07_drafts`. Keep the human Super Admin login separate.
4. Once the overprivileged API token is revoked, remove **only** the mistakenly provisioned `$HOME/media07-private/listmonk-draft-credential.json` via a reviewed interactive `rm -i` (never print the file); run `python3 $HOME/media07-03-candidate/deploy/media07/provision-draft-credential.py` again to write the **new restricted** account/token. Verify mode 0600 and ownership, without disclosing values.
5. Independently inspect the assigned roles and exact list scope in listmonk before any connector activation. Preserve the existing staging Compose and WordPress status.

**Fail-closed caveat:** The current Python adapter does not independently introspect user roles. An operator-created Super Admin API credential may pass its token file syntax checks. A least-privilege role review and proof of **no send** are therefore mandatory acceptance gates, not optional preferences. Do not record MEDIA-07.3 as deployed/accepted until completed.

## Current acceptance and remaining risks

- [x] Mock-provider tests cover absent/incorrect bearer, wrong role, cross-organization request, disabled feature flags, nonempty/public list, safe write path, result draft validation, error redaction, duplicates, and no-send route contract.
- [x] CI tests run as part of MEDIA-07 plus MEDIA-06 regression; reference precise green run from PR after validation.
- [ ] **Live API authentication** against listmonk v6.2.0 on Contabo, with least-privilege token.
- [ ] Real listmonk campaign response/body round-trip and content rendering verification.
- [ ] Durable idempotency/audit registry or single-writer guarantee. Current query-then-create deduplication is **not atomic across processes**; it cannot be used as an unqualified production delivery guarantee.
- [ ] Distinct verified human approvals (MEDIA-06/Workspace), accepted Newsletter Studio draft ownership, signed WordPress bridge, source provenance, full email-client render validation.
- [ ] No production subscriber list, opt-in, suppression/unsubscribe, SMTP, public routing or publication.

**Operator go/no-go:** A private local listmonk installation is not the same as a deployed authenticated draft connector. If any credential, list permission, per-organization isolation or backup gate is uncertain, leave `SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED=0` and do not create the campaign.


## 11 November 2026 — Signed Newsletter Studio handoff candidate, v8.9.3

This supersedes the outdated credential status above. The operator interactively removed the mistaken local credential file and successfully reprovisioned a 0600 private file for sc_media07_drafts. Custom MEDIA07 Draft Connector and MEDIA07 Staging List Access role assignments were reported, but exact API privileges, the private zero-subscriber list, and proof of denied send **still require live verification**.

### Source build added to draft PR #34
- WordPress Newsletter Studio v8.9.3 has a manual **Create private listmonk staging draft** button. Disabled unless all separate WordPress bridge configuration constants are present.
- Only an exact saved private Studio revision can be transferred; both title and subject must begin with [SYNTHETIC], and the administrator must explicitly attest that the contents are synthetic. The PHP AJAX handler validates the CSRF nonce, saved canonical project/subject/preheader SHA, and revision number. It computes the actual rendered HTML hash.
- WordPress PHP sends the exact JSON bytes over configured HTTPS to an independently gated Python bridge using HMAC-SHA256(timestamp + newline + body), without exposing the bridge key, backend URL, listmonk token, or service identity key to browser JavaScript. It only accepts an explicit unsent draft response and saves a private revision-bound receipt.
- New Python module backend/app/media07_studio_bridge_v1290.py authenticates the timestamp and HMAC **before** parsing the body, has a two-minute validity window, checks staging/tenant/danger/synthetic gates, and calls the existing draft-only listmonk adapter.
- No send, schedule, test send, subscriber import, list selection, provider URL selection, or automatic syndication was introduced.

### Secure configuration — values must not be committed or shared
WordPress wp-config.php constants:
- SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED (boolean; disabled until authorized)
- SCEC_MEDIA07_STUDIO_BRIDGE_URL (exact approved HTTPS URL ending /v1/newsletter-studio/bridge/drafts; no query, redirect or nonstandard port)
- SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY (separate randomly generated key, minimum 32 characters; never the listmonk token or identity signing key)
- SCEC_MEDIA07_STUDIO_ORGANIZATION_ID (exact allowed staging UUID)

Additional isolated Python canary env vars:
- SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED=1 (default off)
- SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY (same separate key as protected WordPress config)
- Existing SCEC_ENV=staging, SCEC_IDENTITY_MODE=bound, SCEC_MEDIA07_STAGING_ENABLED=1, SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED=1, SCEC_ALLOWED_ORGANIZATION_IDS, SCEC_MEDIA07_DRAFT_ORGANIZATION_ID, SCEC_MEDIA07_EMPTY_LIST_ID, SCEC_MEDIA07_LISTMONK_CREDENTIAL_FILE and a distinct SCEC_IDENTITY_SIGNING_KEY remain mandatory.

**Connectivity gate:** Bluehost cannot reach Contabo localhost 127.0.0.1 without an approved service connection. Do not expose the general backend or listmonk publicly. Any future HTTPS private bridge must have an approved ingress access policy and verified TLS. Production flags, DNS, reverse proxy, SMTP, subscribers and existing listmonk Compose are unchanged.

### Canary acceptance, NOT yet executed
1. Verify the exact private active zero-subscriber list; prove the restricted sc_media07_drafts API role cannot send, schedule, alter status, or manage recipients. Revoke old Super Admin token if not already revoked.
2. Start a distinct single-worker Python staging canary on an approved local bind with all feature flags disabled first. Keep existing MEDIA-05/06 and production untouched; verify host-local listmonk connection.
3. Exercise signature, timestamp, wrong-tenant, non-synthetic, unsafe HTML, stale revision and disabled-route negative tests. Check WordPress nonce and cross-user isolation.
4. Only after a separately approved private HTTPS ingress is ready, enable bridge flags for a synthetic saved Studio revision and click the manual draft action. Verify one listmonk draft, zero subscribers, repeat-click reconciliation, and **zero additional Mailpit messages**.
5. Record revision, SHA, source commit, list ID, campaign ID, receipt, negative tests, rollback and bridge-disabled postcondition.

**Known limitations:** This does not independently prove browser-compiled HTML corresponds to the exact saved MJML or that an independent human approved the draft. HMAC requests can be replayed inside 120 seconds; listmonk search-then-create reconciliation is not atomic across workers/hosts, so use exactly one canary writer. Production requires durable idempotency, signed editorial approval, trusted render proof, actual role verification, and privacy/consent controls. Source-only build is not deployed or accepted.
