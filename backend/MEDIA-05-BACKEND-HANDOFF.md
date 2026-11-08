# MEDIA-05 / E&C backend integration handoff

**Branch target:** `Content-Catalyst-LLC/sustainable-catalyst-engagement-communications`, stacked after MEDIA-04.

## Source changes

- `backend/app/media_bridge_v1250.py`: new private, metadata-only status/preview contract and blocked action endpoints.
- `backend/app/main.py`: mounts the new router behind **existing** `require_service_token` dependency. No existing route is changed.
- `backend/tests/test_media_bridge_v1250.py`: contract, auth, tenant, review, blocked actions and dangerous-flag tests.
- `wordpress-bridge/.../includes/media05-bridge.php`: protected WordPress admin interface and server-initiated HTTPS request.

## Controls

`SCEC_MEDIA05_STAGING_ENABLED=0` by default. To use the preview, deployment must explicitly set it to 1 **together with** bound identity mode, token verification, organization allowlist and exact public source host allowlist. The existing `offline_staging.scope()` also demands that dangerous production flags stay 0. The preview cannot persist, publish or contact any external platform.

Backend and WordPress both validate the same package-ref and approved SHA-256 fingerprint. WordPress rechecks MEDIA-04's approval against the live public source. The backend treats rights and approval facts as **WordPress attestations only**. The source URL is never fetched by the backend. Responses never contain draft bodies or personal contacts.

Backend integration is **an authenticated staging bridge**, not a fully federated system of record. Actual production publishing, two-person approval, durable cross-product campaign records, idempotent queues and delivery provider authorization require later build gates.

## Next accepted build

MEDIA-06: production-grade owner identity and two-person review, persisted tenant-scoped cross-product reference, reconciliation/idempotency, authorized provider adapters (subject to platform APIs), audited rollback and production deployment acceptance. No provider access tokens in public WordPress data tables.
