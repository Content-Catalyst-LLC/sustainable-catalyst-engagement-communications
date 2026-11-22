# SCEC-R01 — Schema reconciliation findings

2026-10-28. **GO for preserving the existing production table schema unchanged; NO-GO for production deployment or corrective DDL.** This scoped decision does not certify recovery, data, roles, identity, privacy or the other release gates.

## Source and evidence

- Production application checkout: `280c6b9516f9a9cafca0682f7656964077367d7d` (backend v8.6.0).
- Approved merged v12.2 baseline with repair: `381a5a382c9b613136c091d0c1f235f36907c037`, tree-identical to tested `d16bf44202de38db90aebdd29283b88febb71d1b`.
- Actual main database: `scec_engagement_v820`; independently retrieved administrator metadata reports revision `850_001`, 18 public tables, owner `scec_engagement_migrator`.
- Original production fingerprint: `08a7bd472d4239c374ba655b2ade1844d216c3acd8a2cc1fd4fe61db885cb381`; original synthetic fingerprint: `38f1a9fa093e72785551064e5749a7d8e3b819c5b97da3073524e6b56ee97704`. Both remain recorded; neither was rewritten or relabeled as an exact match.
- Full administrator metadata is retained privately at mode 0600. Sanitized precise differences are in `schema-structural-differences.json`; executable comparer and producer hashes are recorded separately.

## Exact differences

All 18 table names, 159 column descriptors/order, 70 indexes, constraint names and RLS-enabled flags match in the exported metadata. Of 68 constraint definitions, 49 match exactly; **19 CHECK definitions differ only in VARCHAR-to-TEXT array cast placement**. No column/type/default/nullability/identity/generated change, missing/extra object, index definition difference or constraint rename was reported.

Example:

```sql
-- Synthetic stored definition:
CHECK (classification::text = ANY (ARRAY['internal'::character varying::text,
 'confidential'::character varying::text, 'restricted'::character varying::text]))
-- Production stored definition:
CHECK (classification::text = ANY (ARRAY['internal'::character varying,
 'confidential'::character varying, 'restricted'::character varying]::text[]))
```

The affected checks are the 12 canonical classification checks, submission-privacy check, two import-batch checks, audit-operation check, support-history check, advisory-approval-state check and advisory-history-event check. The JSON diff lists every exact table/constraint and both strings. No SQL expression was silently normalized by the comparison tool.

## Serialization, version and isolated semantics

Canonical JSON key sorting and named-collection sorting do not remove the mismatch. Production running version and isolated test server both report **160015 / PostgreSQL 16.15**; Ubuntu versus Debian packaging differs. There is no current major/minor version mismatch to blame. Exact historical creation/parser provenance is not established.

The 19 exact pairs were strictly validated as the same named column and same ordered literal list, using only the observed VARCHAR/TEXT cast forms. On an isolated PostgreSQL 16.15 restore, 380 allowed, invalid, case, whitespace, boundary and NULL cases produced identical truth values and CHECK acceptance. The built-in VARCHAR-to-TEXT cast was observed as binary-coercible. Recreating the production-deparsed CHECK definitions in that isolated restore produced the **synthetic fingerprint**, not the original production fingerprint: deparse/reparse converts these stored representations to the tested target form. This is explicit representation/round-trip evidence; it does not change the original production hashes or establish exact historical creation circumstances.

`check-cast-equivalence.json` records all results, including `production_fingerprint_reproduced_in_isolation=false`, `production_definitions_reparsed_to_expected_fingerprint=true`, 19 checks / 380 cases, and owned-container cleanup. The earlier operator attempt incorrectly required reproducing the original stored fingerprint after reparsing; that assertion failed, and the corrected test reports the observed round-trip behavior explicitly. An earlier SQL-extraction operator error was corrected. These were isolated operator failures, not production changes or hidden compatibility passes.

## Migration lineage

Read-only production-source hashes match target source for revisions `830_001`, `840_001`, `850_001`, canonical models, persistence models and audit models. Only `820_001` intentionally differs: PR #22 limits bootstrap creation to its original 13 tables. Current production already records head `850_001`; applied revisions should not be rerun or stamped to repair a hash. No production Alembic command was executed. The stored head and matching source artifacts are lineage evidence, not a complete historical execution audit.

## Writers and identities

All seven SCEC units v8.0–v8.6 are enabled and active as OS user `catalystadmin`. Inspected v8.0–v8.2 main modules contain no persistent-handler references; v8.3–v8.6 contain persistent handlers but explicitly run with persistence=0. No runtime database URL or database target in protected v800/v860 configuration was found. Therefore no PostgreSQL application login is configured/observed for these current services; **do not infer the DB login from the OS user or database owner**.

Effective metadata: `postgres` is login/superuser; `scec_engagement_migrator` is login/non-superuser and owns the database/tables. Both have SELECT/INSERT/UPDATE/DELETE/TRUNCATE over the 18 inspected tables. Built-in `pg_write_all_data` is NOLOGIN and has INSERT/UPDATE/DELETE, not SELECT/TRUNCATE; no relevant memberships were returned. These are possible administrative/privileged write paths, not proof of actual current app traffic. No connections were observed. The checked cron/unit paths yielded only the seven SCEC unit-file candidates; this is not an exhaustive external/manual writer attestation.

All table RLS-enabled flags are false in both schemas. This is not a mismatch or permission to enable RLS blindly; tenant isolation must be verified at the applicable application/database boundaries in R03. Keep future application credentials least-privileged and separately approved. No grants were altered.

## Decision and limits

The observed fingerprint discrepancy does **not** justify production schema repair. Retain the existing DB unchanged; do not drop/recreate CHECKs, rerun bootstrap migrations, change grants, stamp history or delete any database. The eight other SCEC-named databases remain preserved; names/ownership alone do not authorize disposal or prove their purpose/content.

This comparison covers the exported table/column/constraint/index/RLS-enabled fields. It is not a full audit of data, collations, triggers/functions/extensions, RLS force/policies, administrative access, external writers or backup consistency. Complete R02 recovery and R03 security, along with privacy and other gates, before cutover. Production deployment remains **NO-GO**. No production data, DB schema, privilege, service or deployment configuration was modified; all test writes occurred only in an owned isolated synthetic container, which was removed.
