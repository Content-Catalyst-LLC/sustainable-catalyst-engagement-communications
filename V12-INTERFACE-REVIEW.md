# v12 dependency and interface review

Owner confirmed the simulation-only scopes in GitHub issues4 and5. v12 starts only after v11.9 staging closed at `60c2a49d537978a37312462ef46bc770d01fadbe`, with918 tests on each host and all seven live gates pending. This is no production authorization. No new service, storage, registration, delivery adapter or dependencies are required.

| Milestone | Reuse / minimal incremental gap |
|---|---|
|12.0 unified objects|Existing v11 object/source references and preview fingerprints. Add frozen typed lineage nodes, explicit artifact/research revisions, hash-checked parent links and graph integrity. Do not rewrite v11 outputs.|
|12.1 calendar planning|Reuse v11.6 time validation/UTC conventions; add offline dependency, embargo and blackout checks. No cron/calendar writes.|
|12.2 campaign bundles|Link v12.0 evidence and v11 channel contracts; produce bounded synthetic variations, no recipients.|
|12.3 rights/purpose|Reuse strict reviews and v11.7 access restrictions; add explicit purpose/consent/retention/embargo simulations. Missing metadata denies.|
|12.4 separation of duties|Reuse bound request administrator authorization; simulate distinct editorial/scientific/legal/privacy reviewer identities as opaque synthetic references. No production role changes or approval-to-send transition.|
|12.5 templates|Use bounded typed content and v11.8 escaping. Add accessible Sustainable Catalyst structured templates, not a new frontend renderer.|
|12.6 accessibility|Inspect structured headings/links/alt text and reviewed locale metadata. No external translation service or automatic publication.|
|12.7 distribution simulation|Reuse idempotency/retry-preview concepts; estimate synthetic plans without queues, mail servers or network.|
|12.8 evidence ledger|Extend hash-checked lineage with reproducible bounded audit bundles. Hashes establish integrity, not source authenticity. No persistent telemetry.|
|12.9 integration assurance|Invoke actual v11/v12 functions with common fixture lineage, adversarial/failure tests and exact-source staging recovery evidence. No live certification.|

## Contract conflicts and decisions

- Historical v11.0 uses a production review gate rather than a uniform production_certified field. v12 uses its own authoritative disabled envelope and never infers approval from absent fields.
- Fingerprints differ by module: manifest_sha256, content sha256 and envelope sha256 have distinct meanings. Preserve hash kind/release and declared source digest; do not pretend every legacy hash covers all output fields.
- Event sequence is integer; other artifact revisions are strings. Preserve explicit artifact revision separately from canonical research revision; no silent cross-version coercion.
- Identifier validation is limited to syntax/checksum/shape; no DOI/ORCID/ROR ownership or registration assertion. Retraction/correction notices remain linked, not flattened away.
- IANA timezone data is a host prerequisite; output times are UTC. New planning contracts must retain caller-declared clocks and assumptions.
- Existing approval booleans do not establish real consent, legal permission, tenant federation trust or production acceptance. New contracts use strict booleans and deny missing review metadata.
- New lineage nodes contain only bounded opaque references, enumerated types/releases and hash links, not arbitrary raw preview dictionaries or contact data. Source digests remain declared references unless independently regenerated from a validated fixture; a matching hash is not a signature or authenticity certificate.
- Every node must belong to the same tenant and research revision, cite registered root provenance and be reachable from one research root. Parent digests must match current node digests; reject duplicates, orphans, cycles and stale links.
- No public endpoints or CORS expansion. Each new module remains default-off under existing service authentication, allowlisted tenant and administrator role; dangerous flags fail closed.

One separately packaged and fully Mac/Contabo-tested release at a time; source preflight and16 protected files unchanged; exact-SHA isolated loopback server stopped after smoke. User-owned /home/catalystadmin release directories use the previously approved staging approach, not sudo or a production workaround. v13 remains blocked until v12.9 closes.
