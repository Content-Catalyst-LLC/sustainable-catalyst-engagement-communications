# MEDIA-07 — Newsletter Studio and self-hosted delivery foundation

**Status: CODE CANDIDATE ONLY. NOT DEPLOYED. NO EMAIL SENDS AUTHORIZED.**

## Decision

- Use **GrapesJS + MJML** for Sustainable Catalyst's future branded visual newsletter editor.
- Use **listmonk v6.2.0** (AGPLv3) as a distinct, self-hosted subscription/campaign/delivery service.
- Use **Mailpit v1.32.0** in isolated staging as the only email capture target; it does not relay externally.
- Keep Substack a **manual optional export channel**, not a dependency or subscriber-sync authority.
- WordPress (Bluehost) remains the website; Python (Contabo) remains the editorial API; listmonk gets its **own** database and lifecycle. No changes to MEDIA-04/05/06 required for this foundation.

## Implemented in this candidate

- `compose.staging.yml`: dedicated PostgreSQL and listmonk containers, loopback-only admin 127.0.0.1:18898, and loopback-only Mailpit inbox 127.0.0.1:18899. No publicly bound DB or SMTP port. All Docker volumes are MEDIA-07-specific.
- `/v1/newsletter-studio/status`: identity-gated, staging-only feature readiness (explicitly does **not** claim live connection).
- `/v1/newsletter-studio/plan`: deterministic, bounded, tenant-authorized no-contact newsletter destination manifest; no HTML or recipient data accepted.
- All send/subscribe/import/schedule/dispatch endpoints stay unavailable.
- Offline tests verify no delivery, duplicate channel and recipient field rejection, and deterministic planning.

## Staging deployment **after operator review and approval**

1. Confirm a dedicated filesystem path, backup/rollback plan, disk headroom, and isolated Docker network on Contabo; do not reuse WordPress, Research, MEDIA-06, or Workspace DBs.
2. Create a **private** env file outside git with `MEDIA07_DB_PASSWORD`, `MEDIA07_ADMIN_USER`, `MEDIA07_ADMIN_PASSWORD`. Protect it with `chmod 600`. Do not paste actual credentials in logs, GitHub, or chat.
3. Check `docker compose --env-file /protected/path/media07.env -f compose.staging.yml config --quiet`. Verify **only** localhost host-port bindings before launch.
4. Start the project with `docker compose --env-file /protected/path/media07.env -f compose.staging.yml up -d`. Verify database healthy, listmonk admin at localhost 18898, and Mailpit admin at localhost 18899.
5. In listmonk, create only a dedicated synthetic test list. Configure SMTP to **mailpit:1025** within the Docker network for capture-only tests. Do **not** configure a public sending provider, import real subscribers, or share public signup links.
6. Keep `SCEC_MEDIA07_STAGING_ENABLED=0` until authenticated offline API tests pass. Do not expose these routes via Caddy or WordPress.
7. Demonstrate captured synthetic test mail and no external delivery, isolated DB backup/restore, auth isolation, opt-out/unsubscribe enforcement, and audit receipts **before** contemplating an external SMTP transport.

## Integration work remaining

- Newsletter editor SPA with GrapesJS, MJML compilation, brand tokens (black/white/pure red), responsive preview, editable source JSON, asset/media library.
- Signed editorial permission bridge to MEDIA-06 with independently verified reviewers and immutable approved content hash.
- Provider adapter that creates **draft-only** listmonk campaigns from approved compiled email; never grants the editor authority to change campaign status.
- Reliable sync between newsletter draft revisions and listmonk draft IDs, no subscriber exports into WordPress, and no mailing without explicit, logged release.
- Listmonk double-opt-in subscriber landing/confirmation/unsubscribe pages; rights/privacy/retention, suppression and provider bounce feedback; SPF/DKIM/DMARC alignment and operational safeguards.
- Production sender domain verification, per-list consent records and cold-start throttling; safe external SMTP configuration, emergency halt, backup and recovery rehearsals.
- Substack export of compatible rich text/assets with manual paste/review, no promise of HTML/CSS fidelity or provider API.

## Licenses

listmonk uses AGPLv3: keep it as a separate service with its attribution and license intact, and review obligations (especially if modifying or exposing it over the network). GrapesJS and the GrapesJS MJML plugin use BSD-3-Clause. Mailpit is a staging dependency only. Verify third-party versions and image digests at deployment.

## Do not misrepresent completion

This branch wires the staging foundation and offline planning contract into the existing Engagement backend. It does **not** mean listmonk or the visual editor has been deployed, subscriber signups exist, or any actual newsletter can be sent. MEDIA-06 must remain off until its independent staging gates pass.
