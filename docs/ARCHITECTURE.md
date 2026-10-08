# v8.0.0 service boundaries

This release is a **new additive foundation**. Legacy systems are NOT replaced or proxied. No persistence, PII ingestion, contacts transfer, email sending, or WordPress mutation is implemented.

| Domain | Responsibility | v8 authority |
| --- | --- | --- |
| support | Cases, knowledge, releases | Legacy FastAPI v7.8.1 |
| contacts | Private intake, dossiers | Legacy WordPress v2.0.2 |
| advisory | Proposals, meetings, billing | Legacy WordPress v2.0.2 |
| newsletters | Generation, templates, Substack-friendly export | Planned |
| forms | Forms, surveys | Existing survey features pending migration |
| tests | Question banks, attempts, grading | Planned |
| assessments | Rubrics, evaluation and provenance | Planned |
| analytics | Engagement events and aggregate insights | Planned |
| integrations | API bridges and shared contracts | Foundation descriptors only |

`ObjectRef` is a stable legacy source pointer, NOT evidence of access or verified ownership. `HandoffEnvelope` is a validation-only request. The validate endpoint never performs a write or action. Private information must not be placed in `attributes` until tenant authorization, retention and privacy policies exist. No auto publishing or AI sending.

Migration order: inventory / backing up legacy → identity/privacy gates → read-only adapters → reconciliation → carefully staged writes → parity tests → switch-over. Preserve WordPress roles, protected uploads, quarantine, recovery procedures and audit history.
