# MEDIA-07 Visual Newsletter Studio · WordPress candidate 8.9.1

**Status:** source implemented on feature branch, automated checks pending/required, **not yet Bluehost deployed or real-account browser accepted**. Sending remains Substack-only and manually initiated by an editor in Substack.

## What is built
- WordPress Settings → **Newsletter Studio (MEDIA-07)** accessible to `manage_options` administrators.
- GrapesJS 0.23.6 + grapesjs-mjml 1.0.8 drag-and-drop MJML email editor; 3 branded templates (research bulletin, policy digest, institutional update).
- Sustainable Catalyst content blocks: feature header, story, evidence highlight, editorial note, red divider, source reference.
- WordPress Media Library image insertion (HTTPS images), desktop/mobile canvas views, sandboxed compiled HTML preview.
- Internal title, email subject and preheader; private newsletter post type `scec_newsletter`, explicitly nonpublic/non-REST.
- Save private revisions via WordPress admin AJAX with capability and nonce enforcement, bounded JSON, a 25-entry SHA-256 revision receipt log, basic stale-revision rejection and autosave after first manual save.
- Editor JSON, MJML and compiled HTML client-side exports; Substack-compatible simplified rich text / image clipboard export with an explicit fidelity warning. Substack **does not support arbitrary custom HTML/CSS**.
- No mail transport, contact export, newsletter auto-send, Substack API or login, email provider keys, subscriber records, public issue feed, nor new Caddy/Contabo routes.

## Build / packaging
GitHub Actions `.github/workflows/media07-studio.yml` pins npm dependencies, vendors browser JS/CSS locally into the **artifact ZIP**, runs PHP/JS safety tests and assembles `scec-newsletter-studio-8.9.1.zip`. A plain Git archive of source has no vendored dependencies; **use the successful Actions artifact ZIP for installation**.

Only when the workflow is green, an authorized Bluehost operator can:
1. Back up Bluehost WordPress database and the currently installed plugin directory/ZIP; do not alter wp-config keys.
2. In WordPress Plugins → Add New → Upload Plugin, upload the CI artifact ZIP; replace the existing Sustainable Catalyst Media & Communications Bridge plugin, **do not install alongside**.
3. Confirm plugin version 8.9.1 and Settings → Newsletter Studio (MEDIA-07) works in an authenticated administrator browser.
4. Test a new bulletin and all 3 templates, drag text/image/story blocks, edit text, mobile view, WordPress image picker and private autosave.
5. Save; reload the page; reopen the newsletter and verify the revised content and subject/preheader persist. Test two tabs: stale revisions must return a conflict rather than silently overwrite.
6. Export MJML, editable JSON, compiled HTML; verify HTML in standard email previews; check the simplified Substack clipboard in a **Substack draft only**, never send for acceptance.
7. While signed out, verify no newsletter draft appears in public WordPress search, REST, feeds or /media/. Verify MEDIA-04 package workflow and MEDIA-06 config screen unchanged.
8. Verify no newsletter route can send mail; the listmonk staging Compose file remains **deferred and not to be deployed**.

## Security & release limitations
- Initial editor is WordPress-administrator-only and private to Bluehost, not yet unified Workspace SSO. WordPress roles/nonce protect save/load but do not represent independently authenticated MEDIA-06 reviewer attestation.
- GrapesJS project JSON is accepted only from a privileged administrator, never served directly by PHP. **Do not permit untrusted/imported projects** until HTML/MJML sanitization and asset URL policy are fully hardened.
- Revision counter checks are not an atomic multi-user locking protocol; simultaneous save and complete rollback/history-restoration still need acceptance.
- CDN fallback exists only for non-vendored source checkouts; release ZIP vendors pinned JS/CSS. Review vendored package versions/hashes and update processes before production approval.
- Browser compiler must return zero errors before HTML preview/download. Some email clients differ; test in mobile, Outlook and Gmail. Emails can include external images: inspect sources and rights.
- Substack export flattens complex layout to conventional rich text/images. Manual verification of images, formatting and source links in Substack is required.
- Unsubscribe and consent remain inside Substack because Sustainable Catalyst performs **no sends**.

## Rollback
Back up before replacement. Restore the previous v8.9.0 plugin ZIP and database backup if necessary. MEDIA-07 private posts/meta may remain stored on WordPress even after restoring older code, so do not delete them without retention review. MEDIA-05/06 Caddy and Contabo services are not modified. Do not enable any MEDIA-06 delivery flags.

## Next development
Research/Library block picker, schema-level document validation, independently authenticated role/review model, asset provenance, email-client compatibility suite, and future premium-provider adapter gated behind separate owner approval. Substack remains primary.
