# v11.6.0 — Event and webinar distribution staging

Baseline v11.5.0: `f58b4a7d43908c998c5b232c311cd30eda4dc00d`.

Existing-service `/v1/events/status` and POST `/v1/events/preview` require bound service identity, allowlisted tenant and administrator role, with default-off `SCEC_EVENTS_STAGING_ENABLED=0`. Any dangerous runtime flag denies the preview. All seven production acceptance gates remain pending. No frontend, WordPress, migrations, database or dependencies changed.

The synthetic contract contains event/webinar type, opaque event reference, integer revision, title/description, canonical HTTPS reference, explicit start/end/update timestamps, IANA timezone, source references and synthetic speaker attribution. Speakers require independent attribution and privacy reviews; event editorial, rights and privacy reviews are also strict booleans. Draft, suppressed or incompletely reviewed events have no ICS output. No actual speaker/contact PII, attendee lists, registration credentials, streaming tokens or private webinar links are supported.

Timezone inputs must carry explicit offsets and whole seconds. Start/end local clock and offset must match host IANA timezone rules, including DST ambiguity and non-existent times; duration is compared in UTC. ICS always emits UTC, so no VTIMEZONE component or client timezone database is required to interpret the generated schedule. The host timezone database remains a validation prerequisite; system database updates may change acceptance of historical/future local inputs. This is not a claim of globally pinned timezone data.

The bounded [RFC 5545](https://www.rfc-editor.org/rfc/rfc5545) VEVENT preview uses CRLF, escaped text, UTF-8-aware folding at 75 octets, deterministic tenant-scoped UID, caller-supplied DTSTAMP/LAST-MODIFIED, SEQUENCE, UTC start/end and explicit status. It has no METHOD, ATTENDEE, ORGANIZER, alarm or remote attachment. Calendar imports and writes are outside this service. No scheduler, calendar client, invitation or broadcast connector is introduced.

Draft/scheduled/completed/cancelled lifecycle labels are explicit metadata, not an executed workflow. A cancellation requires a positive revision and notice; every positive revision requires a notice. Stable UID connects updates while the evidence hash changes. This stateless preview cannot verify historical revision monotonicity or whether an event actually occurred; it does not persist or certify an event history. Cancellation previews are not dispatched.

Blocked routes: register, invite, broadcast, write-calendar, publish, send, schedule, delete and federate. Even fully reviewed administrator requests cannot enable them. All authoritative publication, transport, persistence, human-login and production states remain false.

See deployment/V1160-DEPLOY.md. Close only after full Mac and isolated Contabo tests, source preflight, complete archive verification, protected-file comparison, exact-commit HTTP safety checks and owned-process shutdown. Do not begin v11.7 before this gate closes.
