# MEDIA-07.3 — Authenticated LIVE listmonk staging acceptance

**Status (2026-11-11):** Guarded local acceptance runner committed in source. **Actual Contabo execution and live provider acceptance have NOT been performed by ChatGPT.** No connected SSH/terminal channel is available here. A browser snapshot and GitHub CI are not live acceptance.

## Scope

Run actual authenticated listmonk API requests on **Contabo localhost only**, using the restricted dedicated API credential, with the production Python draft adapter and signed FastAPI handler exercised in-process. No new Docker service, public route, Bluehost production change, subscriber import, sending or scheduling. One hard-coded synthetic campaign draft can be created and reconciled **only with explicit operator opt-in**.

This can certify a live-provider in-process vertical slice, **not** a deployed HTTPS bridge, WordPress browser, or production release.

## Baseline

- Private listmonk UI/API: http://127.0.0.1:18898 (existing Caddy proxy; do not rerun its Compose installer).
- Mailpit capture-only API: http://127.0.0.1:18899/api/v1/messages.
- Restricted credential: HOME/media07-private/listmonk-draft-credential.json (owned by catalystadmin, file mode 0600; never print/upload/share).
- Read-only listmonk browser snapshot shows sc_media07_drafts with MEDIA07 Draft Connector user role and MEDIA07 Staging List Access list role. It **does not** prove the exact assigned permissions, private empty list ID or denied send behavior. A separate older Super Admin API user named tahmad appears in the snapshot; review and revoke unused privileged tokens safely, without removing the normal human administrator.

## Gate A — inspect assigned roles and private list (read-only)

In listmonk Admin -> Users, confirm sc_media07_drafts is an API user with the expected two custom roles and NOT Super Admin. In Admin -> Users -> User roles, inspect MEDIA07 Draft Connector: only campaigns:get and campaigns:manage; campaigns:send, campaigns:get_all, campaigns:manage_all, tx:send, subscriber import/manage/query/read, settings, user management, public archive and any other administration privileges must be absent.

In List roles, confirm MEDIA07 Staging List Access gives read/view on *only* the exact active private list named SCEC MEDIA07 STAGING EMPTY. Confirm that list has subscriber_count=0 and record only its numeric ID. A global lists:get_all or lists:manage_all role bypasses list scoping and is unacceptable.

Do not test the send permission by attempting a live status transition; if the API key is accidentally overprivileged, the attempt could send or schedule a message. If role review is incomplete, **NO-GO**.

References: https://listmonk.app/docs/roles-and-permissions/ and https://listmonk.app/docs/apis/campaigns/

## Gate B — fetch exact candidate and run READ-ONLY preflight on Contabo

From an authorized SSH terminal on the **Contabo host**:

    set -euo pipefail
    cd "$HOME/media07-03-candidate"
    git status --short
    # STOP if the checkout contains unexplained edits.
    git fetch origin feature/media-07-03-listmonk-draft-adapter-20261109
    git merge --ff-only origin/feature/media-07-03-listmonk-draft-adapter-20261109
    git rev-parse --short HEAD
    python3 -m venv .venv-media07-canary
    . .venv-media07-canary/bin/activate
    python -m pip install -r backend/requirements-dev.txt
    python deploy/media07/accept-live-draft-canary.py

Expected READ_ONLY and PREFLIGHT_PASS. The code checks the private API credential, discovers or verifies the exact private active zero-subscriber list (optional --list-id NUMBER), queries only matching synthetic campaigns and reads Mailpit baseline. No campaign is created in default mode.

If dependencies are already available in a suitable isolated Python environment, reuse them without installing unrelated packages. Do not run this on the Mac: localhost there refers to the Mac's SSH tunnel, while the credential and source are on Contabo.

## Gate C — create/reconcile one synthetic draft, explicit approval

Only if Gates A and B are both satisfied, on the same Contabo terminal:

    cd "$HOME/media07-03-candidate"
    . .venv-media07-canary/bin/activate
    python deploy/media07/accept-live-draft-canary.py \
      --execute \
      --roles-reviewed \
      --synthetic-acknowledged

The runner mints **ephemeral independent keys in its own process**, invokes the real FastAPI signed bridge handler through TestClient, and sends its synthetic fixture to real listmonk localhost using the dedicated restricted API user. It calls the handler twice; requires both results to reference the same campaign, second call to reconcile an existing draft, then checks exact draft body, list membership and status. Before/after Mailpit message totals must match.

On full success it writes a redacted local-only receipt to HOME/media07-private/acceptance/MEDIA07-03-LIVE-CANARY.json and prints LIVE_PROVIDER_DRAFT_PASS, duplicate_reconciled=true and mailpit_delta=0. It records that **programmatic send-permission denial and deployed Bluehost HTTPS bridge are NOT verified**. It never prints credentials, does not retry uncertain POSTs and does not delete, send, schedule or expose a campaign.

If any step fails, **NO-GO**. Review the private state before retrying. The script only alters environment variables inside its own process: existing deployments and production flags are unchanged.

## Gate D — full WordPress-to-Contabo staged integration (NOT done by Gate C)

Required separately: deploy an isolated single-writer Python canary, private authenticated HTTPS ingress from Bluehost (Bluehost cannot access Contabo localhost), secrets provided only through approved server-side channels, install/test the v8.9.3 WordPress plugin after backup, verify saved revision/nonce and cross-user isolation, and execute the manual synthetic draft action twice with one resulting draft and zero Mailpit increment. Document rollback and approved network restrictions. Leave every send/subscriber/publication gate off.

**Full MEDIA-07.3 release remains BLOCKED** until Gate D and independent permission verification succeed. Source-only mocked CI or an in-process live provider acceptance is not equivalent to a deployed authenticated Newsletter Studio bridge.
