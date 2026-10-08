# Changelog

## 8.1.0 — Canonical Data & Object Model
- 12 strict Pydantic canonical object contracts.
- Source-qualified legacy identifiers, UUIDs, tenant reference, timestamps, classification.
- Read-only authenticated model catalog and individual JSON Schema endpoints.
- Additional validation and compatibility tests.
- No database migration, records, or production writes.

# Changelog

## 8.0.0 — Unified Platform Foundation
- New consolidated platform identity and modular Python package.
- Nine domain descriptors with source and migration status.
- Shared validated contracts for references, objects and non-executing handoffs.
- `/health`, `/v1/capabilities`, `/v1/contracts/handoff/validate`.
- Fail-closed production startup for missing/weak service credentials.
- Migration safety and legacy mapping documentation.
- Automated foundation tests; no changes to existing repositories.
