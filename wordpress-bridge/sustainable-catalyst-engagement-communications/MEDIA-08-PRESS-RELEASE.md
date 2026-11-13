# MEDIA-08 Press Room — WordPress 8.9.2 review candidate

**Source committed on stacked [PR #32](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/pull/32). Not installed or browser-accepted on Bluehost. Live publication remains disabled by default.**

## Existing code reconciliation
- Reuses the institutional Press renderer and brand CSS already developed in [PR #24](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/pull/24).
- Preserves existing `[sc_media]` and compatibility `[sc_press]` as the general Media hub. New `[sc_press_room]` specifically renders a Press landing and its approved-only archive. No menu or WordPress page is automatically changed.
- Existing optional legacy /press/ and /channel/ redirects remain unchanged until a *real* WordPress /press/ page exists; the current collision guard prevents redirecting such a page. Host and SEO redirects must be independently inspected.
- Existing synthetic newsroom (v11.2), media relations (v11.4), editorial planning (v12.1), campaign composer (v12.2), and [PR #20](https://github.com/Content-Catalyst-LLC/sustainable-catalyst-engagement-communications/pull/20) structured templates are **not activated as live publication**. Avoid parallel implementation until backend reconciliation.
- Newsletter Studio adds a manual Press announcement block and link to Press admin, not an automatic newsletter send.

## Implemented
- Private, nonpublic, non-REST WordPress CPT `scec_press_release`; private admin editor under **Settings → Press Room (MEDIA-08)**.
- Release types: press release, announcement, statement, research release, institutional update, methodology note, data release, event notice.
- Headline, summary, restricted-HTML body, optional HTTPS source, UTC embargo, source-bound SHA-256 fingerprints.
- Workflow: draft → in_review → approved → released. Edits after submission are blocked; new revisions require new records. Different WordPress admins must submit and review; approver explicitly confirms rights, source integrity, privacy and institutional authority.
- Actual release requires **`SCEC_MEDIA08_PUBLIC_RELEASE=true`**, a published /press/ page with `[sc_press_room]`, current SHA matching approval, distinct reviewer, expired embargo. The public archive independently checks SHA and embargo.
- No outbound SMTP, social posting, press-contact export, sending or private API publication.

## Current limitations and gates
- WordPress reviewer IDs are not certified service-wide human identities; MEDIA-06 private reviewer bridge remains incomplete. Do not enable live releases solely because the WordPress checkboxes pass.
- Archive uses public Press page fragment anchors, not individual canonical press URLs. Durable withdrawal/retention and public revision history remain to be built.
- Anonymously querying a private CPT through a shortcode requires real WordPress/browser acceptance; **do not assume releases appear anonymously** before testing.
- GrapesJS/Javascript visual email editor remains independent of Press admin form. Shared Research/Library evidence/asset picker is a future workstream.

## Bluehost acceptance before cutover
1. Back up current WordPress DB and plugin. Install only a **green CI artifact ZIP** from the feature branch, replacing rather than duplicating the plugin.
2. Test private draft save/reopen, submit, same-author review denial, independent approval and embargo. Keep public-release flag OFF.
3. Create a separate Press page with `[sc_press_room]` only after inventory of /press/, /media/, /channel/, WordPress redirects, SEO rules and navigation; do not overwrite an existing page.
4. Verify anonymous readers never see a private or unapproved object. Verify existing Media, MEDIA-04/05/06, newsletter editor and legacy shortcodes still behave unchanged.
5. Record admin/browser acceptance, backup and rollback. Do not enable release without separate production approval.

## Rollback
Restore prior plugin ZIP and WordPress DB backup. MEDIA-08 private records persist if database is not reverted; no automatic delete. No Contabo services or secrets are affected.

**CI:** PHP validation, lint and disposable listmonk/Mailpit synthetic capture are defined in the feature branch. Check workflow conclusions at the exact commit before claiming a pass; CI passing would not establish a live Bluehost/Contabo deployment.
