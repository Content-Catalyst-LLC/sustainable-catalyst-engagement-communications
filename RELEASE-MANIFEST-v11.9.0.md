# v11.9.0 — Synthetic audience analytics and v11 assurance

Baseline v11.8.0: `e0452613d5cee1f48fe20fa8a0bf6472517d5bf3`.

Default-off `SCEC_AUDIENCE_STAGING_ENABLED=0`; `/v1/audience-analytics/status` and POST `/preview` require bound service identity, allowlisted tenant and administrator role. All dangerous flags deny access. Tracking, collection, identity export, publication, sending, activation, deletion and federation routes remain503.

Only bounded synthetic fixture events are accepted: opaque synthetic event/reader IDs, object/revision, channel, view/engage type, date and declared source edition. Nested tenant and source references must match. Matching synthetic view evidence is required for each engagement on the same reader/channel/object/revision. Identical event-reference replays are deduplicated; conflicting duplicates reject the entire batch. Counts are distinct synthetic readers within each channel, not inflated event volume.

Minimum group size is a strict integer between5 and50, default5. Any nonzero readership or engagement cell below threshold withholds the whole table, including all channel labels and totals; no small residual can be computed from returned marginals. The output never includes event/reader IDs. Zero engagement is explicitly distinguishable from an unsafe small nonzero cell. All source editions, canonicalized deduplicated inputs and method version are evidence-bound.

This is a synthetic regression contract, not a production anonymization guarantee: no differential privacy, cross-query privacy budget, real consent verification, identity resolution or causal attribution. Hashes are integrity fingerprints, not a promise of irreversible anonymization. Shares are descriptive synthetic proportions. No actual readership, tracking pixels, subscriptions, browser telemetry, analytics connector or historical query occurs.

The cross-release integration test invokes actual v11.0–v11.9 functions using one tenant, research object, revision and source. It verifies stable source-manifest lineage through partner routing, explicit identifiers and notices, reviewed/unreviewed alert/press/event/embed behavior, deterministic results, pending production gates and no socket transport. Historical module release identities are preserved. v11.0 expresses its production block in review_gates.production_acceptance and requires_live_production_acceptance rather than a production_certified field; adapters must not assume uniform historical response fields.

See V11-READINESS.md and deployment/V1190-DEPLOY.md. No new dependencies or changes to protected frontend, WordPress, migrations, Alembic configuration or production. Final closure requires exact-commit full Mac/Contabo suites, preflight, protected-file and source/archive checks, loopback HTTP negative checks and clean shutdown. Seven live gates remain pending. v12 must start only after the v11.9 staging gate is closed and the confirmed v12 scope/interface matrix is reviewed.
