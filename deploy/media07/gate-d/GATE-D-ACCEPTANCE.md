# MEDIA-07.3 Gate D — WordPress Newsletter Studio to Contabo end-to-end acceptance

**Status:** Gate D implementation candidate in PR #34; **NO deployed cross-host acceptance yet**. Gate C passed on 11 November 2026 with synthetic list #3, campaign #2 and Mailpit delta 0. The actual Contabo shell, Bluehost WordPress admin, private tunnel/DNS settings, provider roles and tokens must be operated/approved by authorized owners. Never mark Gate D accepted merely because GitHub CI passed.

## Trust boundaries and source changes

- WordPress Studio **v8.9.4**: an authenticated administrator saves a *private* revision containing canonical GrapesJS project JSON **and browser-compiled email HTML**. WordPress validates bounded inert HTML, retains a private exact compiled HTML artifact and its SHA-256, and computes the revision fingerprint over canonical project, subject, preheader and HTML SHA. Old revisions from v8.9.3 or earlier require an explicit re-save before staging. WordPress no longer accepts separate browser-supplied HTML at synchronization time; it reads only the stored HTML and verifies hashes before signing. Browser independently re-compiles and compares SHA with the saved version in secure HTTPS context before enabling the transfer.
- Staging-only PHP AJAX requires \`manage_options\` and nonce, private post, matching exact revision, [SYNTHETIC] title and subject, explicit checkbox and server-side compiled-HTML validation. It sends JSON over verified HTTPS, no redirects, using timestamp/body HMAC-SHA256 and optional server-only Cloudflare Access service-token headers. URL/HMAC/Access/listmonk credentials never appear in browser JS or public metadata.
- Contabo **isolated gateway** \`backend/app/media07_studio_gateway_v1291.py\` imports only the signed draft router, **not** the general \`main.app\`. Only POST \`/v1/newsletter-studio/bridge/drafts\` is allowed (other app endpoints 404); OpenAPI/docs disabled. Signed handler is default OFF unless all staging/identity/single-tenant/send-deny feature flags and an independent scoped HMAC key match. Real adapter hard-codes local listmonk, checks exact active private zero-subscriber list #3 before creating/reusing a draft, and never calls send/schedule/subscribers APIs.
- The compiled HTML is stored from the *authenticated editor's browser*. Comparing its hash after reload provides evidence of consistent browser rendering. It is **not** independent server-side MJML recompilation or human editorial approval, so only synthetic acceptance content is in scope.
- A non-atomic listmonk search/create dedupe remains: permit **one** canary worker, avoid parallel Gate C or WordPress writers, and treat ambiguous timeouts as reconciliation events requiring manual review, not an automatic retry.

## D0 — prerequisite owner security and backup checks (no write to live stacks)

1. Review \`sc_media07_drafts\` roles in listmonk and independently prove \`campaigns:send\`, \`tx:send\`, subscriber import/manage, status mutation and global/Super Admin grants absent. The \`--roles-reviewed\` flag from Gate C was an operator attestation, not programmatic privilege denial. Never probe \`PUT /campaigns/{id}/status\` with a real credential.
2. Confirm list #3 is **SCEC MEDIA07 STAGING EMPTY**, private/active with 0 subscribers. Confirm Gate C draft campaign #2 remains in \`draft\`; record its existing ID so a separate WordPress fixture is not confused with it.
3. Record current Mailpit total (Gate C ended at 1) and a timestamp. If another staging process changes Mailpit, pause and reconcile with timestamps rather than attributing all changes to the newsletter.
4. Verify Contabo backup/recovery capacity and snapshot current Bluehost plugin and staging WordPress database. Do not attempt Bluehost production plugin upgrade before staging browser success.
5. Approve the HTTPS ingress architecture and domain ownership separately. The source never installs Cloudflare, changes DNS, opens inbound firewall ports, deploys a reverse proxy or enables a production sender.

## D1 — prepare a LOCAL ONLY isolated API canary on Contabo

From an authorized \`catalystadmin\` SSH session on **Contabo** (no passwords/tokens in chat/logs):

\`\`\`bash
set -euo pipefail
cd "$HOME/media07-03-candidate"
test "$(git branch --show-current)" = feature/media-07-03-listmonk-draft-adapter-20261109
test -z "$(git status --porcelain)"  # stop if local worktree is dirty
git fetch origin feature/media-07-03-listmonk-draft-adapter-20261109
git merge --ff-only origin/feature/media-07-03-listmonk-draft-adapter-20261109
. "$HOME/media07-private/venv-canary/bin/activate"
(cd backend && python -m pytest -q tests/test_media07_studio_gateway_v1291.py tests/test_media07_studio_bridge_v1290.py)
# Safe one-time private-file creation. Will NOT overwrite an existing env file.
python deploy/media07/gate-d/provision-env.py --provision-synthetic-staging
python deploy/media07/gate-d/preflight.py
\`\`\`

Require \`GATE_D_PREFLIGHT_PASS private_list_id=3 subscriber_count=0\`. The provisioner writes two different random private secrets under \`~/media07-private/gate-d.env\` (0600) and never outputs them. If a prior Gate D environment file exists, stop and inspect it offline instead of deleting/recreating it. The HMAC value must be conveyed **only through an approved secure secrets channel** to the staging Bluehost server. Keep the listmonk API credential entirely on Contabo.

Install the user service *only after* reviewing its exact ExecStart and local bind:

\`\`\`bash
mkdir -p "$HOME/.config/systemd/user"
install -m 0644 deploy/media07/gate-d/scec-media07-gate-d.service \
  "$HOME/.config/systemd/user/scec-media07-gate-d.service"
systemctl --user daemon-reload
systemctl --user start scec-media07-gate-d
systemctl --user --no-pager --full status scec-media07-gate-d
ss -ltn | grep ':18903'
\`\`\`

Check the listener is **127.0.0.1:18903** only; stop immediately if it binds to 0.0.0.0, ::, or a public address. No \`systemctl --user enable\`, \`loginctl enable-linger\`, general Engagement API restart or Compose change is authorized here. This process is for a supervised acceptance session; it may terminate when the owner SSH session ends.

Read-only/negative checks against the loopback canary:

\`\`\`bash
curl -sS -o /dev/null -w 'docs HTTP %{http_code}\n' \
  http://127.0.0.1:18903/docs
curl -sS -o /dev/null -w 'send HTTP %{http_code}\n' \
  -X POST http://127.0.0.1:18903/v1/newsletter-studio/listmonk/send
curl -sS -o /dev/null -w 'unsigned draft HTTP %{http_code}\n' \
  -H 'Content-Type: application/json' -d '{}' \
  http://127.0.0.1:18903/v1/newsletter-studio/bridge/drafts
\`\`\`

Require \`docs HTTP 404\`, \`send HTTP 404\`, \`unsigned draft HTTP 401\`. These requests cannot create a draft or send email. Do not expose \`127.0.0.1:18898\`, \`18899\` or \`18903\` on public interfaces.

## D2 — approved private HTTPS service connection (Bluehost -> Contabo)

**NOT INSTALLED by this PR.** Choose and authorize one of the following before attempting a cross-host browser test:

- **Cloudflare Tunnel + Cloudflare Access Service Auth** if the target domain is actually managed by Cloudflare. Route one dedicated HTTPS hostname to Contabo \`http://127.0.0.1:18903\` through cloudflared (no inbound origin port). Protect the entire hostname with a default-deny Access self-hosted application whose sole \`Service Auth\` policy includes a uniquely scoped, short-lived service token issued for this Bluehost staging integration. Enable strict service-token authentication where available. WordPress PHP supplies the \`CF-Access-Client-Id\` and \`CF-Access-Client-Secret\` headers **server-side**, in addition to its independent HMAC. There must be **no ordinary Allow bypass policy**. Verify unauthorized external callers get 401/403, and a properly Access-authenticated request without HMAC still gets 401. Cloudflare Tunnel creates a hostname reachable at the edge; it is not an acceptable private ingress until the Access policy is enforced and tested.
- An independently approved **mutually authenticated TLS or private-network ingress** with equivalent origin restrictions and only the single-purpose gateway as upstream. Bluehost outbound networking restrictions and trustworthy certificate validation must be confirmed. No plain HTTP, trust-all TLS, shared public listmonk endpoint or general Engagement API exposure.

Do not change authoritative DNS just to run this test. If the approved private channel is not ready, **STOP Gate D at D1** and keep the gate status BLOCKED.

Authoritative Cloudflare docs: https://developers.cloudflare.com/tunnel/get-started/ and https://developers.cloudflare.com/cloudflare-one/access-controls/service-credentials/service-tokens/

## D3 — staged WordPress plugin and private configuration

After a staging WordPress DB backup, previous plugin ZIP/hash and rollback plan are verified, deploy the **v8.9.4** PR-built ZIP to a **staging WordPress** instance. Do not install it on Bluehost production as a shortcut.

Set WordPress server-side constants in the private staging \`wp-config.php\` (fill in only from the secure credentials handoff, never GitHub/chat/screenshots):

\`\`\`php
define('SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED', true);
define('SCEC_MEDIA07_STUDIO_BRIDGE_URL',
    'https://<APPROVED-PRIVATE-ACCESS-HOSTNAME>/v1/newsletter-studio/bridge/drafts');
define('SCEC_MEDIA07_STUDIO_ORGANIZATION_ID', '00000000-0000-4000-8000-000000000007');
define('SCEC_MEDIA07_STUDIO_BRIDGE_SHARED_KEY', '<PRIVATE-SCOPED-HMAC-KEY>');
// Include these two constants only for a Cloudflare Access deployment:
define('SCEC_MEDIA07_ACCESS_CLIENT_ID', '<PRIVATE-ACCESS-CLIENT-ID>');
define('SCEC_MEDIA07_ACCESS_CLIENT_SECRET', '<PRIVATE-ACCESS-CLIENT-SECRET>');
\`\`\`

The HTTPS URI must use a trusted certificate, fixed approved hostname and exactly \`/v1/newsletter-studio/bridge/drafts\`. The PHP code disables redirects and verifies TLS certificates. If a managed Access token is used, both header constants must be present (or neither); no Access header/URL/token is localized to browser JavaScript.

## D4 — browser, authorization, provenance and provider acceptance

Use three staged WordPress identities: the permitted administrator who owns a saved *private* synthetic issue, a second administrator with no rights to that issue, and a non-admin. Keep staging WordPress behind an authenticated private URL.

1. Verify the editor is rendered and responsive: change a block, preview desktop/mobile, and save a clearly fictional test issue with **[SYNTHETIC]** in both title and subject. Confirm version v8.9.4 and the revision receipt's SHA values; previous v8.9.3 revisions must be explicitly **re-saved** before they can synchronize.
2. Save the private issue with the browser MJML compiler; reload it from the database, and confirm both the project and **rendered HTML digest** are present. A changed HTML render after reload must be rejected by the browser hash preflight. Editing without saving must block the action.
3. Verify a non-admin cannot view Newsletter Studio and a different administrator cannot list/load/save/synchronize the first owner's private issue. Both must be denied access to the protected data. Verify neither identity can call \`wp_ajax_scec07_sync_staging\`. Invalid nonce and signed-out AJAX must fail. CSRF and stale revision must reject before any remote request. No secrets, backend origin URL, Access headers or listmonk token may appear in browser network requests, JS globals, page HTML or response.
4. Record listmonk private list #3's subscriber count, campaign search state, and Mailpit total **immediately before** the first action. Confirm the UI button is enabled only when the bridge is configured. Tick the explicit synthetic-only confirmation and click **Create private listmonk staging draft** once.
5. Require a success response identifying **one new or reconciled draft ID** (NOT necessarily Gate C's #2), a private WordPress staging receipt bound to the saved revision, listmonk readback with the exact subject/HTML and status \`draft\`, list #3 still at **0 subscribers**, and **Mailpit delta 0**.
6. Click the action again with the identical saved revision: require **same listmonk campaign ID**, \`draft_reused=true\` and no duplicate campaigns. Reload the issue and confirm the private receipt persists, explicitly labeled *not live provider status*.
7. Test negative gates with no provider write: changed/unsaved revision, unsigned or expired HMAC, wrong organization, no Access token, mismatch of stored HTML SHA, missing \`[SYNTHETIC]\`, disabled flags, unsafe markup, forbidden send/schedule/subscriber routes. Verify that an unrelated staging WordPress user cannot inspect another editor's private revision. The exact role must not hold delivery permissions.
8. Preserve sanitized evidence: source commit SHA, plugin ZIP SHA, administrator browser acceptance, list ID, campaign ID(s), before/after Mailpit counts, source and rendered digest, WordPress private receipt, negative results, HTTPS ingress access-log **status codes only**, rollback trial and owner signoff. Store secret-bearing captures only in restricted operator storage.

## D5 — rollback and release decision

To **disable integration immediately**, set \`SCEC_MEDIA07_STUDIO_BRIDGE_ENABLED\` to false on WordPress and disable the private Access policy/route. On Contabo:

\`\`\`bash
systemctl --user stop scec-media07-gate-d
ss -ltn | grep ':18903' || echo 'Gate D loopback listener stopped'
\`\`\`

Verify no new Mailpit traffic, no reopened listener and no change to production listmonk/Media services. If the staging plugin is defective, restore the **backed-up staging** WordPress plugin ZIP and DB with rollback evidence; do not restore a production DB or perform a Docker volume prune.

**Release decision:** Pass only if D0–D5 are independently evidenced. Gate C is PASS; **Gate D remains BLOCKED until a real deployed secure cross-host route and the WordPress browser acceptance steps finish**. The goal is a reusable Newsletter Studio to private listmonk draft workflow, not email dispatch or automatic Substack publication.
