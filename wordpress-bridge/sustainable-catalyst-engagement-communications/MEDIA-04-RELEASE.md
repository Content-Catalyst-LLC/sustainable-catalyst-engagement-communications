# MEDIA-04 — Controlled Editorial Packages & Manual Distribution

**Version:** 8.8.8  
**System:** Sustainable Catalyst Media WordPress Bridge  
**Status:** Local release candidate; **not installed/accepted on live WordPress**

## Implemented

- Adds a **Media Distribution** administrator workspace under WordPress Settings.
- Creates private, nonpublic `scec_media_package` records; no REST route and no public archive.
- Authors a short title, public summary, approved public WordPress source permalink and selected channel list.
- Restricts creation, review, approval, draft generation, external receipt recording and export to `manage_options` and verified POST nonces.
- Enforces `draft → in_review → approved` transitions, reviewer identity/time, rights/attribution and embargo confirmations, and SHA-256 approval fingerprints that include source article contents.
- Prevents edits to submitted packages; source changes after approval invalidate downstream generation, exports and manual posting records.
- Generates **one WordPress editorial post in `draft` state**, never a published post, tagged `media-update`. Editing/publishing takes place in WordPress's ordinary CMS. Public MEDIA-03 discovery observes it only if separately published with opt-in enabled.
- Produces copy-ready text for selected Substack, YouTube, LinkedIn and social channels. A human pastes it into the official provider; there is **no API write**.
- Allows optional public platform URL receipts with host validation. These are **operator-attested and not provider-verified**.
- Exports versioned JSON for later authenticated SCEC/Workspace integration. It is downloaded locally, not sent to a service.
- Preserves MEDIA-01/02/03 shortcode, public page, public feed, redirects, plugin option names and existing administration features.

## Boundaries and gaps

- WordPress remains the editorial publishing authority; this release is **not connected** to private Engagement & Communications, Workspace, Library or Research authorization services.
- No Substack newsletter publishing, YouTube upload, LinkedIn/social automated posts, email sending, contact/subscriber import, external OAuth or token collection.
- Approval currently allows the same administrator to author and review; it logs the reviewer but does **not** enforce a two-person approval policy.
- No off-site source-authority verification: input must resolve to an already-published, non-password-protected, canonical WordPress `post` or `page` on the same HTTPS host.
- External URLs are manual assertions and not fetched. Export must be reviewed before any external ingestion.
- The package's audit trail is a bounded last-100-events private metadata array, not a tamper-evident organization-wide log.

## Acceptance steps

1. Upload/replace plugin ZIP after WordPress/plugin/database backup.
2. Confirm `[sc_media]` and MEDIA-03 public page are unchanged for anonymous visitors.
3. Open **Settings → Media Distribution**, create a package from an already-public local WordPress article, save and submit.
4. As an authorized administrator, review rights and embargo checkboxes and approve the exact source version; see fingerprint status.
5. Create editorial draft once, verify it is **draft**, tagged `media-update`, with an outbound source link. Ensure double clicking cannot create a second draft.
6. Test manual copy text, record a valid external link as operator-attested, export the JSON package.
7. Verify that WordPress source edits invalidate a prior approval, and invalid nonce/capability requests cannot mutate records.
8. Confirm there are no requests to Substack, YouTube, LinkedIn, or other social APIs and no private items appear in the public feed.

## Rollback

Reinstall backed-up v8.8.7 plugin ZIP. No data migration occurs and v8.8.8 does not touch external accounts. Private `scec_media_package` posts/meta **remain in the WordPress database** after rollback; back up the database and retain the package manifest exports before any future cleanup/deletion.

## Next integration build

MEDIA-05 should create a signed, scoped, read-only contract for the separate Engagement & Communications backend to ingest *approved* package metadata after human SSO, tenancy, permissions and production gates have been accepted. Live outbound channel adapters are a later separately authorized release.
