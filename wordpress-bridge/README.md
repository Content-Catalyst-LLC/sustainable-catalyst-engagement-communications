# WordPress bridge v8.8.0

The WordPress plugin uses shortcodes to render a public landing/launch surface. The standalone v8.7.0 app remains separate. **No iframe**, login forwarding, cross-domain tokens, proxy, live API calls, customer data, or database writes. No automatic page creation or route replacement.

Plugin: `wordpress-bridge/sustainable-catalyst-engagement-communications/`.

Install ZIP through WordPress Plugins → Add New → Upload Plugin. Activate it. Add `[sc_engagement_communications]` in a Shortcode block on the desired WordPress page. The optional `[sc_engagement_launch]` renders the launcher only.

WordPress Settings → Engagement Bridge: set the public HTTPS standalone app URL **only after** configuring DNS, Caddy, TLS and verifying the application browser behavior. Until then, the button is replaced with a clearly labeled pending state. The loopback address `127.0.0.1:8097` is never a valid user-facing URL.

The plugin uses WordPress options and Settings API; configuration requires `manage_options`. Styles are scoped to `.scec880`. No front-end scripts, tracking, REST routes, cookies, or persistence in the plugin.


## Press public page (proposal, not yet deployed)

The public-facing **Press** page is distinct from the private Engagement & Communications operating system and from the WordPress **Publications** blog.

Use `[sc_press]` on the WordPress Press page to render an accessible, read-only newsroom directory. It links **only to already-published WordPress pages** (press releases, institutional updates, media resources and press inquiries). Missing pages are explicitly marked *Not yet published*; no fabricated releases, staged records, subscriber information, private drafts, messages or backend calls are exposed. The existing `[sc_engagement_communications]`, `[sc_engagement_launch]`, and `[sc_engagement_public_links]` shortcodes remain supported.

The public-links shortcode now labels the former **Channel** destination **Press**, looking for published `/press/` first and `/channel/` as a compatibility fallback. This does **not** rename the WordPress page or automatically redirect it.

### WordPress activation checklist (separate operator-controlled release)

1. Back up the WordPress site and record the existing `/channel/` page, inbound links, menu assignment and content.
2. Install and test this plugin version on staging. Confirm `[sc_press]` renders and all links are public/published, with no private data or network calls.
3. Rename the existing Channel page's title to **Press**, edit its slug to `press`, and place `[sc_press]` in its WordPress Shortcode block. Retain relevant approved existing content.
4. Update navigation text to **Press**, linking to `/press/`. Keep **Publications** pointing to existing WordPress posts and articles.
5. Add a permanent **301** from `/channel/` to `/press/` after checking for slug conflicts. Do not put a generic catch-all redirect in the plugin.
6. Verify public/anonymous browsing, mobile layout, keyboard focus, internal links, 301 behavior and canonical URL. Roll back the page/menu and plugin changes if acceptance fails.

No service, API, database, repository slug, permissions, live sending or E&C rollout is changed by this WordPress-only proposal.
