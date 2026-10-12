# v8.8.0 WordPress bridge — Mac → GitHub → Bluehost

1. Save the full repository ZIP in `~/Downloads`, unzip, rsync into the existing repository, run the backend suite and lint the PHP plugin. Commands are in the assistant release response.
2. Commit/push the changes to the repository. No backend restart, migrations or Contabo changes are needed for the WordPress plugin.
3. In WordPress → Plugins → Add Plugin → Upload Plugin, upload **the separate** `sustainable-catalyst-engagement-communications-wordpress-v8.8.0.zip` file, activate.
4. Make or edit the WordPress page (e.g. Engagement & Communications). Insert the `Shortcode` block containing `[sc_engagement_communications]`; publish/preview.
5. Settings → Engagement Bridge: leave the HTTPS URL blank until a public standalone application URL is configured and independently verified. You can still use the launch page as an informational preview.
6. When DNS + HTTPS are configured (through a separate audited Caddy reverse-proxy deployment), set the public HTTPS URL. Click the launch link and ensure a new tab opens the correct standalone read-only application, with no API data or credentials exposed.
7. Verify a site theme's CSS does not overwrite scoped styles, check both mobile and desktop, and confirm WordPress diagnostics show no PHP notices.

Rollback: deactivate the plugin. This does not affect the standalone web container on 8097, FastAPI on 8816, or PostgreSQL at schema 850_001. Reverting the WP page can be done independently.

Security boundaries: never put backend secret values into WordPress options, never embed the standalone app in an iframe (it uses `X-Frame-Options`/CSP), no production writes, and do not expose the API directly to browsers.
