# v9.3.0 — Product Support & Case Management

- Staging-only authenticated case classification, severity, escalation, status-transition recommendations, and aggregate summaries.
- No database writes, migrations, email, network actions, persistence, or customer-facing changes.
- Fail-closed staging flag `SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED=0` by default.
- Organization bound to principal, allowlisted, editor/administrator role required.
- All five WordPress pages and their existing plugin unchanged; no live form submission integration.
- Existing v8.4 persistence-capable support routes remain under their prior protections and are **not** replaced or certified by this release.
- Previews are heuristic and require human review. No case history is read or stored.
