# WordPress bridge v8.8.0

The WordPress plugin uses shortcodes to render a public landing/launch surface. The standalone v8.7.0 app remains separate. **No iframe**, login forwarding, cross-domain tokens, proxy, live API calls, customer data, or database writes. No automatic page creation or route replacement.

Plugin: `wordpress-bridge/sustainable-catalyst-engagement-communications/`.

Install ZIP through WordPress Plugins → Add New → Upload Plugin. Activate it. Add `[sc_engagement_communications]` in a Shortcode block on the desired WordPress page. The optional `[sc_engagement_launch]` renders the launcher only.

WordPress Settings → Engagement Bridge: set the public HTTPS standalone app URL **only after** configuring DNS, Caddy, TLS and verifying the application browser behavior. Until then, the button is replaced with a clearly labeled pending state. The loopback address `127.0.0.1:8097` is never a valid user-facing URL.

The plugin uses WordPress options and Settings API; configuration requires `manage_options`. Styles are scoped to `.scec880`. No front-end scripts, tracking, REST routes, cookies, or persistence in the plugin.
