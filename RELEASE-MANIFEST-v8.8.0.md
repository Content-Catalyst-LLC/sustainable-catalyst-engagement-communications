# v8.8.0 — WordPress Compatibility Bridge
- WordPress installable plugin version 8.8.0 with public landing shortcode and optional standalone launcher shortcode
- Settings API HTTPS-only URL configuration, privileged to administrators; no private-loopback/browser credentials
- Scoped CSS, no JavaScript, no API relay, no fake data, no iframe or authenticated session claim
- Backend and frontend of v8.7.0 retained unchanged; migrations: none; database schema remains 850_001
- Source and syntax/security tests in `backend/tests/test_bridge_v880.py`
- Separate plugin ZIP for installing in WordPress
