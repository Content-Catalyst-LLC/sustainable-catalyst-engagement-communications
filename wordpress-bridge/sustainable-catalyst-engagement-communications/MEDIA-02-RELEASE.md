# MEDIA-02: Site activation and safe legacy redirects

**Release candidate:** 8.8.6  
**Scope:** WordPress plugin only; existing Engagement & Communications backend remains unchanged.

## Changes
- Readiness diagnostics in WordPress > Settings > Media & Communications: `/media/` exists, public, shortcode detected, same-site permalink, and legacy source slug collision checks.
- Optional, **default-off**, conditional HTTP 301 redirects from `/press/` and `/channel/` to the published `/media/` permalink.
- Exact slug matching for root and subdirectory WordPress installations; no query passthrough, POST/preview/API redirects, or arbitrary URL destinations.
- Preserve all existing `[sc_media]`, `[sc_press]`, `[sc_engagement_communications]`, `[sc_engagement_launch]`, and `[sc_engagement_public_links]` shortcodes and public channel configuration.
- No automatic WordPress page/menu changes or live backend access.

## Acceptance (administrator)
1. Verify WordPress backup and current plugin backup.
2. Install ZIP, activate, and confirm plugin release 8.8.6.
3. Confirm `/media/` is published and contains `[sc_media]`.
4. Verify Settings > Media & Communications readiness checks show PASS for public page and shortcode.
5. Confirm Substack, YouTube, LinkedIn and configured socials are correct; avoid asserting publication ownership from defaults alone.
6. Verify page while logged out and test mobile/keyboard access.
7. Check source-page collisions and any preexisting host/SEO redirects before enabling conditional plugin redirects.
8. Only then, if needed, enable legacy redirects and verify 301 for `/press/` and `/channel/`, with no loop and no unrelated redirects.
9. Confirm WordPress navigation now reads Media; update outside this plugin if needed.
10. If a check fails, switch legacy redirects off and restore the backed-up plugin/page/menu. Clear caches.

## Out of scope
- Channel feeds/APIs beyond read-only Substack RSS already present in v8.8.5.
- Subscriber storage, media mailing, LinkedIn/YouTube auto-publishing, Research/Workspace SSO.
- WordPress administrator access, CDN/host redirects, live acceptance performed by this build.
