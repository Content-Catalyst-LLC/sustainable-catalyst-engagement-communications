# MEDIA-03 — Unified Channel Discovery (WordPress v8.8.7)

**Packaged source; local QA passed; production not yet accepted.** The `[sc_media]` page can show an optional, server-rendered and cached stream of public Substack RSS issues, YouTube Atom uploads (explicit 24-character UC channel ID required), and *published WordPress posts explicitly tagged* `media-update`. It links to source publishers; it does **not** post content to external channels, transmit subscribers, or access private Engagement & Communications data. No external feeds are fetched until the owner enables discovery in **Settings → Media & Communications**.

The feed uses safe HTTPS-only 5-second/256-KB fetches with redirects disallowed, source-host validation, XML parse safeguards, 60-minute positive and 10-minute negative caching, and a visible empty state. Public source availability, WordPress SimpleXML and anonymous browser behavior require live acceptance.

See [MEDIA-03 release notes](sustainable-catalyst-engagement-communications/MEDIA-03-RELEASE.md), [MEDIA-03 local test report](MEDIA-03-TEST-REPORT.md) and [installation instructions](sustainable-catalyst-engagement-communications/INSTALLATION.txt). MEDIA-02 v8.8.6 readiness checks, legacy 301 redirect safeguards and old shortcodes remain supported. Target site: `https://sustainablecatalyst.com/media/`.

---

# MEDIA-02 — Public Media activation candidate v8.8.6

The public WordPress hub is now **Media** at the intended `/media/` page, while the internal backend remains **Engagement & Communications**. This plugin build includes [sc_media], legacy [sc_press] compatibility, Substack, YouTube, LinkedIn and public social links. It also adds **Settings → Media & Communications → MEDIA-02 Launch readiness** and conservative, optional legacy redirects.

**Release status:** source packaged and local QA passed; **not yet live-accepted or merged**. Use the ready-to-upload ZIP, review `sustainable-catalyst-engagement-communications/MEDIA-02-RELEASE.md`, and test from a logged-out browser. Legacy redirects are disabled by default. No emails or social posts are sent.

---

# WordPress bridge v8.8.0

The WordPress plugin uses shortcodes to render a public landing/launch surface. The standalone v8.7.0 app remains separate. **No iframe**, login forwarding, cross-domain tokens, proxy, live API calls, customer data, or database writes. No automatic page creation or route replacement.

Plugin: `wordpress-bridge/sustainable-catalyst-engagement-communications/`.

Install ZIP through WordPress Plugins → Add New → Upload Plugin. Activate it. Add `[sc_engagement_communications]` in a Shortcode block on the desired WordPress page. The optional `[sc_engagement_launch]` renders the launcher only.

WordPress Settings → Engagement Bridge: set the public HTTPS standalone app URL **only after** configuring DNS, Caddy, TLS and verifying the application browser behavior. Until then, the button is replaced with a clearly labeled pending state. The loopback address `127.0.0.1:8097` is never a valid user-facing URL.

The plugin uses WordPress options and Settings API; configuration requires `manage_options`. Styles are scoped to `.scec880`. No front-end scripts, tracking, REST routes, cookies, or persistence in the plugin.
