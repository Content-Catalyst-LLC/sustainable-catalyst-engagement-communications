# MEDIA-03 — Unified Channel Discovery and Syndication

**Version:** v8.8.7  
**Target:** WordPress /media/ public page  
**Status:** Packaged candidate; not production-accepted

## Included

- Opt-in, read-only unified *Latest from our channels* stream.
- Substack RSS feed of public newsletter issues using the configured publication root (also works with approved custom domain).
- YouTube public Atom feed using an explicitly provided UC channel ID; two fixed first-party feed paths are supported as best-effort fallback.
- Selected WordPress `post` entries explicitly tagged `media-update`, and only published/non-password-protected posts.
- Server-side XML parsing with network/resource limits, blocked redirects, restricted source links, de-duplication, reverse chronological ordering, text-only sanitized titles, and clear empty-state fallback.
- Hour-long positive feed cache and 10-minute negative cache using WordPress transients; no subscriber data and no scheduled outbound jobs.
- WordPress administrator settings and local configuration/readiness summary.
- Existing public Media design, Substack subscription links, YouTube click-to-play, LinkedIn/social directory, Press/Channel redirect gates, and previous shortcodes are preserved.

## Scope of "syndication"

MEDIA-03 **aggregates links to already-public source material** on the Media page. It does **not** post to LinkedIn, YouTube, X, Substack or any other external publisher. Authenticated posting, content rights approval and channel delivery are separate future work.

## Safety and acceptance

- Auto discovery is **OFF by default**; a WordPress administrator must enable it.
- Only configured Substack publication host and fixed YouTube public feed host are fetched; arbitrary feed URLs are not accepted.
- No additional MEDIA-03 feed requests when unified discovery is disabled. The pre-existing Substack recent-issues RSS feature remains controlled separately by its own checkbox. No client-side RSS fetch or tracking pixels.
- Public items shown only after successful source validation. Transient network errors do not expose private details to visitors.
- PHP SimpleXML is required for auto parsing; the admin diagnostics report its availability.
- Test the page while logged out, WordPress content privacy, source links, feed failures, mobile display, and cache refresh before marking live acceptance.

## Rollback

Disable **Unified public updates** under Settings > Media & Communications and save. The previous Media page layout remains. If necessary, restore plugin v8.8.6 using the saved ZIP. No content or account records are migrated and no external delivery occurs.
