# MEDIA-06 — Editorial Operations, Candidate v8.9.0

**Status:** Implemented on feature branch; tests, migrations, real-user approval and deployment acceptance remain. NOT merged, NOT deployed, NOT production-certified.

## Product boundary
- WordPress /media/ public page and MEDIA-04 editorial source remain unchanged.
- MEDIA-05 metadata-only preview endpoints remain unchanged and can stay disabled.
- MEDIA-06 adds signed, tenant-scoped editorial registration, two-reviewer approval, reconciliation, evidence logging and a private WordPress admin screen.
- No direct external publishing, subscriber/contact export, credentials, provider API, or email sending.
- This is an isolated staging implementation. It is not federated user authentication or a production campaign queue.

## Security model
Bluehost signs a fresh 90-second, RS256 request-bound assertion for every admin action using a 3072-bit RSA private key stored outside the WordPress document root. The Contabo backend holds only the public key(s). Each assertion binds the HTTPS issuer, tenant UUID, subject, audience, key ID, expiry, method, full path/query, and raw request-body SHA-256. The backend verifies the identity and tenant allowlist, the staging flag, and existing danger flags before accepting requests. There is no static bearer to copy across servers. Rotation of the longer-lived RSA keypair remains an operator-controlled task and is NOT automatic.

**Important limitation:** Reviewer identities are asserted as WordPress numeric user IDs (wp:user:123) and signed by the same site service key. Backend enforces one submitter and two distinct reviewer IDs, but does not independently verify actual humans. This is not sufficient production two-person authorization until independently authenticated reviewer identity is built and tested.

## Implemented workflow
1. An authorized WordPress administrator opens Settings > Media Operations (MEDIA-06).
2. A currently approved MEDIA-04 package is registered as immutable package/approval SHA-256 metadata; no draft body transferred.
3. Repeating the same idempotency key and exact input returns the same record. A conflicting key fails. A new approval fingerprint creates a new revision and supersedes the prior one.
4. The submitter cannot review. Two different other WordPress actor IDs must approve before state becomes approved. Duplicate reviews and stale fingerprints fail; rejection is final.
5. Private audit and approved-fingerprint reconciliation show differences; no actual send is possible.

## Backend routes — NOT Caddy-exposed yet
- GET /v1/media-ops/status
- POST /v1/media-ops/packages
- GET /v1/media-ops/packages/{id}
- POST /v1/media-ops/packages/{id}/reviews
- GET /v1/media-ops/packages/{id}/audit
- GET /v1/media-ops/packages/{id}/reconcile?approved_sha256=...
- POST /v1/media-ops/publish, /send, /schedule, /enqueue always return 503.

## Database and feature flags
The operator-applied backend/migrations/MEDIA06_CREATE.sql creates ONLY media06_packages, media06_reviews, and media06_audit with tenant/revision/idempotency uniqueness, composite org/package foreign keys, and append-only review/audit DB triggers. No automatic schema change runs from the app.

Keep both feature gates OFF until isolated backup, migration, restore, tenant-isolation, race, and reviewer acceptance pass:
SCEC_ENV=staging
SCEC_IDENTITY_MODE=bound
SCEC_MEDIA06_ENABLED=0
SCEC_MEDIA06_STORAGE_ENABLED=0
SCEC_MEDIA06_ISSUER=https://sustainablecatalyst.com
SCEC_MEDIA06_PUBLIC_KEYS_FILE=/home/catalystadmin/media05-staging/media06-public-keys.json
SCEC_MEDIA06_DATABASE_URL=postgresql+psycopg://DEDICATED_DB_USER@DEDICATED_HOST/scec_engagement_media06

Only a manually approved dedicated database named scec_engagement_* is eligible. Do not use Workspace, Research, Library, or WordPress databases. Existing MEDIA-05, research API and Caddy routes stay in place.

## Key provisioning (staging only)
On Bluehost, never inside public_html, with umask 077:
    mkdir -p "$HOME/media06-private"
    chmod 700 "$HOME/media06-private"
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$HOME/media06-private/bridge.key.pem"
    chmod 600 "$HOME/media06-private/bridge.key.pem"
    openssl pkey -in "$HOME/media06-private/bridge.key.pem" -pubout -out "$HOME/media06-private/bridge.pub.pem"

Transfer ONLY the public PEM through an approved administrator-controlled channel. Pin its contents under the exact key ID in a JSON mapping file on Contabo; do not put it in GitHub. Never paste a private key, service token, environment secret or database credential into chat or a public log.

In the protected Bluehost wp-config.php after review:
    define('SCEC_MEDIA06_ENABLED', false);
    define('SCEC_MEDIA06_KEY_ID', 'bluehost_media06_20261108');
    define('SCEC_MEDIA06_PRIVATE_KEY_PATH', '/home1/pctrqumy/media06-private/bridge.key.pem');
Existing SCEC_MEDIA05_API_ORIGIN and SCEC_MEDIA05_ORGANIZATION_ID are reused. No token is stored in wp_options.

## Operations / roll-forward / rollback
- Verify backend/PHP tests and WordPress plugin v8.9.0 syntax and installation first.
- Run manual database migration after backup and migration approvals; verify backup/restore and least-privilege grants.
- Only then configure public key and set service/storage staging flags to 1 in a controlled maintenance window.
- Caddy requires a separate restricted routing change for MEDIA-06; not part of this source build. Keep /health and all unrelated paths blocked; no public port 18891.
- Real administrator tests: signed status; registration; duplicate and changed revision; two distinct reviewers; rejection; reconciliation; audit; no external delivery.
- Rollback: disable MEDIA06 flags on both hosts, remove only the MEDIA-06 Caddy route if applied, restore v8.8.9 WordPress plugin. Preserve evidence tables for retention review; do not drop data.

## Acceptance not complete
- [ ] New backend and PHP CI green.
- [ ] Real WordPress installation test and isolated PostgreSQL migration/restore.
- [ ] Concurrent review and tenant isolation against real database.
- [ ] RSA key rotation/revocation and complete short-lived assertion lifecycle.
- [ ] Independently authenticated distinct human reviewers.
- [ ] Real TLS Wordpress-to-Contabo registration, review and reconciliation.
- [ ] Publication and delivery remain disabled and verified.
- [ ] Operator change-control and production signoff.

MEDIA-06 implements substantial staging functionality, but does NOT authorize production publishing or subscriber data transfer.

## Migration recovery note (2026-11-08)
Contabo first application stopped with `ERROR: syntax error at or near "$"` in the PostgreSQL audit trigger function. The repository's initial MEDIA06_CREATE.sql had a malformed single-dollar delimiter, fixed on this branch to `$media06$`, with a terminating PL/pgSQL `END;`. The migration ran inside `BEGIN` with ON_ERROR_STOP, so its aborted transaction should have rolled back all created tables; **verify the live state rather than assuming rollback**. The isolated container, persistent Docker volume, restricted env files and the app database role were provisioned before the failed migration. Do NOT repeat the one-shot initialization script or regenerate passwords. Check the container/role and zero MEDIA-06 tables, fetch the corrected branch, then apply only the migration and deferred least-privilege GRANT step. New CI job performs actual disposable PostgreSQL 16 migration and forbidden database-name tests before approving the recovery.

Staging recovery is not a production cutover and does not enable MEDIA-06 or touch MEDIA-05.
