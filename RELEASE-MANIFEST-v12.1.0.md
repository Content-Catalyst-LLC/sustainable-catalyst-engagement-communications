# v12.1.0 — Editorial calendar and planning simulation

Verified predecessor v12.0.0 `b954cf017e98853dd63c4095f55d2dfe2016e02f`.

Default-off `SCEC_CALENDAR_STAGING_ENABLED=0`; existing-service `/v1/editorial-planning/status` and POST `/preview` require bound service identity, allowlisted tenant and administrator role. Any dangerous flag denies access. All seven production gates remain pending.

A frozen synthetic plan contains the validated v12.0 communication object and its exact envelope hash, launch-window artifact pointers, caller-supplied as-of time and optional blackout windows. Stale communication or artifact evidence, missing dependencies, cycles, duplicate windows and cross-tenant references reject the contract. No arbitrary titles, contacts, recipients or raw preview payloads are accepted.

Reuses v11.6 aware-time and IANA-zone validators. Explicit offsets must match the named zone for each local start/end, including DST ambiguity/non-existent times. Positive duration, dependency completion, embargoes, blackout overlaps and past windows are compared in UTC. Intervals that only touch at boundaries do not overlap. Missing embargo/editorial review denies eligibility, even if no embargo timestamp is supplied. A denied dependency propagates denial. No automatic rescheduling or current system-clock lookup occurs; output is deterministic from supplied evidence, constraints and as-of time. The host timezone database remains a validation prerequisite.

Eligibility is a planning result only. No cron, calendar writes, notifications, publishing, sending, activation, deletion or federation is enabled; all corresponding live routes return503. No state is persisted. No frontend, WordPress, migrations, database, credentials or dependencies changed. See deployment/V1210-DEPLOY.md. Full Mac/Contabo regression, preflight, protected16 hash comparison, complete ZIP/source verification and exact-SHA loopback/shutdown evidence are mandatory before v12.2.
