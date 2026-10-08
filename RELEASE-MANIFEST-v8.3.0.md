# v8.3.0 Contact & Engagement Python Migration

* Add opt-in FastAPI/PostgreSQL APIs for organization, contact, inquiry, engagement-event canonical records.
* Reject non-allowlisted tenant ID; reject cross-organization links and duplicate legacy identities.
* Add Alembic `830_001` append-only engagement audit table; record creation in same transaction.
* No WordPress modification, automatic intake, or changes to v8.2 persistence schema.
* Deploy on VPS `scec-v830` port 8813, database schema migrated deliberately.
* This is a foundation for migration; no legacy data has been copied or certified.
