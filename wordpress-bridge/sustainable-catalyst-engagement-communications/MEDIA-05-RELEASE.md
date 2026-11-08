# MEDIA-05 — Engagement & Communications Backend Bridge

**Release candidate:** Media WordPress v8.8.9 + additive Engagement & Communications backend route  
**Status:** Source-built, locally security-tested; **NOT live-connected, NOT merged, NOT production-certified**.  
**Scope:** Admin-initiated, authenticated, nonpersistent preview of an already approved MEDIA-04 public editorial package.

## Product boundary

- **Media** is the public WordPress hub with Substack, YouTube, LinkedIn, and social links.
- **Media Distribution (MEDIA-04)** remains the authoritative WordPress editorial draft/review/approval state.
- **Engagement & Communications** is the separate FastAPI operating system. MEDIA-05 adds a guarded **metadata-only review preview** endpoint, not a production distribution queue or a synchronization service.
- No WordPress public shortcode calls the private backend. No shared login or direct database write is introduced.

## Backend endpoints (not public APIs)

- `GET /v1/media-bridge/status` — signed service token, canonical tenant, administrator role, explicit staging flag and allowlist; returns private preview capability state.
- `POST /v1/media-bridge/preview` — same gate; strict bounded contract: `scec.media-bridge/1`, organization UUID, WordPress package ID, canonical public source URL, SHA-256 source/approval fingerprints, approval timestamp, approved channel list, and three WordPress-attested review assertions.
- All `/v1/media-bridge/{publish,send,schedule,sync,commit,activate,subscribe,export-recipients}` mutations return HTTP 503 even with the correct token; no persistence, external calls, address books, or subscriber data.

The backend validates envelope shape, the private service principal, tenant and allowlisted **source host**. It does **not** independently verify that WordPress approved the source, or check rights/embargo at the source; it labels those claims accordingly. Suggested workflows (`newsletter-alerts` or `campaign-composer`) are advisory labels, not executed work.

## WordPress admin workflow

1. Preserve `[sc_media]` public page and existing MEDIA-04 approved package workflow.
2. Set protected constants in `wp-config.php` **only in a controlled staging environment**:

```php
// Example names only. Provision values through authorized administrators/secret store.
define('SCEC_MEDIA05_ENABLED', true);
define('SCEC_MEDIA05_API_ORIGIN', 'https://APPROVED-PRIVATE-SERVICE-ORIGIN.example');
define('SCEC_MEDIA05_ORGANIZATION_ID', 'REPLACE-WITH-CANONICAL-TENANT-UUID');
define('SCEC_MEDIA05_SERVICE_BEARER', 'REPLACE-WITH-SHORT-LIVED-SIGNED-BOUND-SERVICE-TOKEN');
```

3. Configure backend `SCEC_IDENTITY_MODE=bound`, `SCEC_IDENTITY_SIGNING_KEY` (private), `SCEC_ALLOWED_ORGANIZATION_IDS`, `SCEC_MEDIA05_STAGING_ENABLED=1`, and `SCEC_MEDIA05_ALLOWED_SITE_HOSTS` (exact public WordPress hostname, e.g., `sustainablecatalyst.com`). Keep production-activation/delivery/transport flags disabled and the service behind approved TLS/network controls. Use an authorized **short-lived** principal with `administrator` role; use the existing offline token provisioning path, not a browser token minting route. Tokens expire in 24 hours or less; rotate in protected configuration, never in this chat or a WP settings field.
4. In WordPress open **Settings → Media Backend Bridge**. Review readiness, **Check authenticated backend status**, then choose an already approved, unchanged MEDIA-04 package and click **Review package with backend**.
5. WordPress pins an HTTPS origin, disallows redirects and unsafe requests, validates the backend tenant and no-send flags, and stores only a local receipt digest for the approved package. It does not persist the bearer, submit private content, store subscribers, schedule jobs, or send posts.
6. Confirm the expected preview receipt and absence of any outbound channel deliveries in the staging service logs. Run logged-out `/media/` checks and verify package preview is not exposed publicly.

### Rollback

Remove or set `SCEC_MEDIA05_ENABLED` to `false` in the WordPress server configuration and disable `SCEC_MEDIA05_STAGING_ENABLED` in the backend. This immediately disables all preview requests. Restore the prior v8.8.8 plugin if needed. MEDIA-04 packages and public Media remain intact. There is no MEDIA-05 schema migration or backend persistent record to undo; previously recorded WordPress preview digests are inert metadata only. No redirects or public page changes in this release.

## Acceptance gates outstanding

- Real WordPress-to-Contabo HTTPS authentication (source branch only at present).
- Backend DNS/TLS and network allowlisting; approved service issuer and short-lived principal lifecycle.
- Real administrator/private tenant permission isolation and credential rotation.
- No unexpected outbound network calls, no live subscriber/data transfer, public Media still read-only.
- Coordinated deployment rollback, backups and production operations approval.

This is **NOT** an authorization to enable email, Substack, YouTube, LinkedIn or social posting, SSO, contact sync, or private research transfer.
