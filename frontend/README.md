# v10.1.0 Static application shell
Includes 12 grouped workspaces, local workspace filtering, keyboard escape, mobile navigation, accessible current route and breadcrumbs. No live data, browser authentication, browser storage, direct API requests, writes, outbound communications or deletion. Deploy web separately only after explicit approval.

# v8.7.0 Standalone Web Application

Independent static frontend for Engagement & Communications, with dark institutional visual styling, seven navigable workspaces, accessible responsive navigation and explicitly read-only preview state. All metrics show `—` because no live data source is connected. **No synthetic records are presented as real.**

Security: no credentials, browser tokens, forms, browser storage, direct API calls, analytics, or client-side authorization. v8.6.0 FastAPI remains independent and private; this release does not claim that end-user login or a BFF exists. Production persistence stays disabled.

Run locally with `python3 -m http.server 8097 --directory frontend` from the repository root. Deploy on Contabo with `cd frontend && docker compose up -d --build`. Binds to `127.0.0.1:8097`; optional public Caddy route requires a separate deployment decision. No database migrations.
