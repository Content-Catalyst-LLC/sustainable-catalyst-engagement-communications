# MEDIA-08.3 Visual editing and in-place revisions: plugin 8.9.8

Extends the existing Press Room (`SC_Media08_Press_Room`). No new editor framework, publishing system or database table.

## Editing
- The release body uses the WordPress editor (`wp_editor`): Visual and Code modes, headings (H2–H4), quote,
  preformatted, lists, links, bold/italic and **Add Media** (Media Library, captions via `[caption]`). Named typographic
  entities (`&mdash;`, `&rsquo;` …) are kept so opening and saving unchanged text does not alter it.
- **Preview** (`?scec_press_preview=<id>&rev=current|working|<n>`) renders the record with the public Press Room
  template inside the site theme. Signed-in reviewers only, nonce-bound, `noindex`, uncached; anonymous requests get 403.

## Drafts and submissions
- Drafts are edited in place; every save is a snapshot. **Return to draft** (`reopen`) takes an in-review or approved
  record back to draft and clears approval state, so it must be submitted and approved again.

## Published releases
- **Edit release** creates a *working revision*. The published text stays live and unchanged until the update is
  approved and published; saving text identical to the live text (ignoring browser line endings and trailing
  whitespace) is a no-op.
- **Publish update** requires the exact working-revision fingerprint, the four attestations and a change type:
  - *Editorial update* (wording, layout, formatting, images, clarity): no correction notice; the page shows
    "Updated <date>" and `dateModified`.
  - *Factual correction*: a public note is required and shown on the same page as a dated correction notice and
    `CorrectionComment` in JSON-LD. No separate correction release is needed (the separate-release path remains optional).
- Approval follows the existing rule: an administrator other than the editor, or the configured single-operator owner
  with an explicit self-review declaration, always disclosed as self-review and never as independent review.
- The swap is one database transaction that re-verifies the fingerprint and rolls back on mismatch. URL, release
  reference and original release date never change. Caches and sitemaps are refreshed afterwards.
- Withdrawn releases cannot be edited.

## Revision history
- Append-only snapshots (`_scec_media08_snapshot`): number, UTC time, user, origin (save, update, restore, baseline),
  note, SHA-256 and full content. Releases published before 8.9.8 receive a *baseline* snapshot of their published text
  on first edit; nothing is created by the upgrade itself.
- Compare any two of live, working and snapshot *n* (`wp_text_diff`). **Restore** copies a snapshot into a new working
  revision (released) or a new draft save; history is never rewritten.
- Event log adds `reopened`, `update_saved`, `update_discarded`, `update_published`, `correction_published`.

## Unchanged
Fingerprint definition, embargo, attestations, CSRF nonces and capabilities on every action, tamper detection, kill
switch, withdrawal, sitemap, SEO metadata, Media page integration. No email, remote HTTP or user creation.

## Tests
- `tests/media083-editing-validation.php` (CI): static contract.
- `tests/media081-wp-acceptance.php` phase `revise` and `tests/media081-staging-acceptance.sh` (disposable staging only):
  handler-level and HTTP checks including the signed-in editor, preview and the upgrade path.
