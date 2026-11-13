# MEDIA-04 — Local Release Verification

**Build:** Sustainable Catalyst Media & Communications WordPress Bridge v8.8.8  
**Target:** WordPress `/media/` and private Settings → Media Distribution workspace  
**Build environment:** PHP 8.4 CLI, JavaScript syntax via Node, synthetic WordPress function harness  
**Status:** Source build and local verification PASS; **production installation and real-browser acceptance NOT PERFORMED**

## Test summary

| Verification | Result |
| --- | --- |
| MEDIA-04 direct unit checks (private CPT, authorization, source validation, host validation) | 16 PASS |
| MEDIA-04 end-to-end approval, nonce, draft, record, export and invalidation simulation | 34 PASS |
| Legacy Media page synthetic suite | PASS (48 assertions) |
| MEDIA-02 redirect/readiness suite | PASS (78 assertions) |
| MEDIA-03 feed/discovery suite | PASS (101 assertions) |
| Main plugin and workflow PHP syntax | PASS |
| Existing and MEDIA-04 JavaScript syntax | PASS |
| JSON schema parse | PASS |
| ZIP CRC/integrity, root directory and expected files | PASS |
| WordPress production site/theme compatibility | NOT TESTED |
| Live data processing, browser acceptance, actual external integrations | NOT TESTED / NOT ENABLED |

Legacy test suites share some assertions, so counts above are reported by suite, not as unique production-certified tests.

## Security and scope checks

- Packages are stored using a private, non-REST custom post type with administrator-only capabilities.
- State-changing requests require `POST`, `manage_options`, a matching action-specific nonce, a valid package, and appropriate workflow stage.
- No private or password-protected article can authorize a distribution package.
- Approval stores reviewer/UTC time and a SHA-256 fingerprint of package data and authoritative public source content.
- Source revisions invalidate approval and block exports, outbound receipt records and WordPress draft creation.
- One generated WordPress article is a **draft only**, tagged `media-update`, and cannot be duplicated through repeated action.
- Approved channel text can be copied; all actual external publishing is manual. Entered external URLs are host-checked and explicitly marked operator-attested, not verified.
- JSON export is downloaded locally; there is no API write, auto-posting, subscriber ingestion or cross-product identity integration.
- Prior MEDIA-01/02/03 user shortcodes and settings are preserved.

## Required live acceptance before calling it deployed

1. Back up active WordPress plugin and database; stage the v8.8.8 ZIP.
2. Verify `Settings → Media Distribution` is visible only to authorized administrators.
3. Test source post restrictions, rights/embargo confirmations, approved fingerprint, audit events and generated draft.
4. Confirm anonymous `/media/` shows **only published** Media/WordPress material, never private package contents.
5. Verify the site theme, permissions, email behavior, click-to-copy and WordPress editor compatibility.
6. Ensure no automatic messages or posts are sent to Substack, YouTube, LinkedIn or other social providers.
7. Confirm rollback to v8.8.7 and private DB records retention through a backup/restore rehearsal.

## Package

- Filename: `sustainable-catalyst-media-wordpress-MEDIA-04-v8.8.8.zip`
- SHA-256: `9d1650425502cec11bba09111c93db434d60d8b1c9c81ebb76e7abd8300fb530`
- Archive includes 11 runtime/documentation files.
