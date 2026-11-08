# MEDIA-03 local QA and installation handoff

**Build:** MEDIA-03 · WordPress v8.8.7  
**Package:** `sustainable-catalyst-media-wordpress-MEDIA-03-v8.8.7.zip`  
**SHA-256:** `32c09ecda8d7be4e33880005c3e5301a99eab57bca6acdb085a11c37d59eb6e4`

## Local verification

- WordPress v8.8.6 compatibility and MEDIA-02 redirect test suite: **78 PASS**.
- New MEDIA-03 feed and site-content integration synthetic checks: **23 PASS**.
- Total **101 PASS**; PHP syntax valid, JavaScript syntax valid, ZIP integrity clean.
- Tests stub WordPress functions and simulate feed parsing. PHP CLI here lacks SimpleXML, so **real XML parsing on the installed WordPress host has NOT been verified**.
- Live HTTP fetch to Substack/YouTube, WordPress activation, anonymous page inspection and 301 redirects: **NOT PERFORMED**.

## Test fixtures and mitigations

- Discovery opt-in defaults off; unconfigured sources do not fetch.
- Valid YouTube UC channel ID accepted, invalid IDs rejected.
- Server-side requests limited to HTTPS, 5-second timeout, 256 KB response, zero redirects.
- Two fixed YouTube feed endpoints, both cached; failures degrade to link-only/empty state.
- Feed item links restricted to expected source hosts; YouTube video URLs constructed from validated IDs.
- Dedupe by canonical source URL, publish-date descending, max six visible items.
- Cross-domain feed links, mismatched channel IDs, unpublished and password-protected WordPress posts excluded.
- WP posts require deliberate `media-update` tag; no arbitrary blog imports.
- Existing `[sc_media]`, legacy `[sc_press]`, settings, social channels and MEDIA-02 redirects retained.

## Required live acceptance

1. Back up plugin and download previous v8.8.6 ZIP before replacement.
2. Install ZIP; verify Settings > Media & Communications > MEDIA-03 diagnostics, including SimpleXML availability.
3. Keep discovery disabled until verified source URL and YouTube UC channel ID are entered.
4. Enable discovery; view /media/ signed out; inspect Substack, YouTube and tagged WordPress links.
5. Test unavailable feeds, stale cache, responsive layout, and accessible reading order.
6. Confirm legacy redirects separately; do not enable if old pages are still active.
7. Mark production acceptance only after a human checks real live WordPress results.

## Exclusions

No automatic outbound syndication to external services, no newsletter sending, no OAuth tokens, no private contact data, no subscriber acquisition metrics, no cross-product identity wiring, no CDN/menu modifications.
