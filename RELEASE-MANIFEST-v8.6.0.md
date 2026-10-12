# v8.6.0 release manifest
- Phase: Identity, Authorization & Privacy
- Base: v8.5.0 `850_001`
- Migration: none (retain `850_001`, 18 tables)
- Tests: 71 passing (local, no live PostgreSQL certification)
- Security: opt-in bound HMAC service principals; RBAC; tenant claim bound to organization header; actor reference checks; non-PII denial telemetry
- Writes: disabled by default
- VPS: localhost port 8816, independent service
- Remaining: issuer/credential lifecycle, persisted audit, operational privacy controls, live PostgreSQL isolation certification
