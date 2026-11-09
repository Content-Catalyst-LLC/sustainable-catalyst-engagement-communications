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

## Current acceptance and remaining risks

- [x] Mock-provider tests cover absent/incorrect bearer, wrong role, cross-organization request, disabled feature flags, nonempty/public list, safe write path, result draft validation, error redaction, duplicates, and no-send route contract.
- [x] CI tests run as part of MEDIA-07 plus MEDIA-06 regression; reference precise green run from PR after validation.
- [ ] **Live API authentication** against listmonk v6.2.0 on Contabo, with least-privilege token.
- [ ] Real listmonk campaign response/body round-trip and content rendering verification.
- [ ] Durable idempotency/audit registry or single-writer guarantee. Current query-then-create deduplication is **not atomic across processes**; it cannot be used as an unqualified production delivery guarantee.
- [ ] Distinct verified human approvals (MEDIA-06/Workspace), accepted Newsletter Studio draft ownership, signed WordPress bridge, source provenance, full email-client render validation.
- [ ] No production subscriber list, opt-in, suppression/unsubscribe, SMTP, public routing or publication.

**Operator go/no-go:** A private local listmonk installation is not the same as a deployed authenticated draft connector. If any credential, list permission, per-organization isolation or backup gate is uncertain, leave `SCEC_MEDIA07_LISTMONK_DRAFT_ENABLED=0` and do not create the campaign.
