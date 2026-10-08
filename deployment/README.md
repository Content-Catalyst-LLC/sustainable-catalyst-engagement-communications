# Deployment notes

This is a *separate port, localhost-only smoke-test deployment* and not a production replacement. Verify port availability with `ss -ltn | grep ':8810 '`. A service unit, environment file, HTTPS reverse proxy, observability, secrets manager, backups, and operational security review are prerequisites for public traffic. Never point legacy WordPress shortcodes to v8.0.0 foundation APIs.
