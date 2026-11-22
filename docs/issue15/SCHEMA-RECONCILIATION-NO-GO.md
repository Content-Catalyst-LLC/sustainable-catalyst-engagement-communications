# Schema reconciliation — explicit NO-GO

2026-10-28. Owner reports administrator findings: main database `scec_engagement_v820`, revision `850_001`, 18 tables, production schema fingerprint `08a7bd472d4239c374ba655b2ade1844d216c3acd8a2cc1fd4fe61db885cb381`; corrected synthetic fingerprint `38f1a9fa093e72785551064e5749a7d8e3b819c5b97da3073524e6b56ee97704`. Fingerprints differ. The structural rows were not included in the summary, so an actual structural diff and compatibility decision remain pending. Do not infer schema incompatibility or safety from either the count or hashes alone.

**Recommendation: NO-GO for production migrations, grant changes, database deletion, service changes or deployment while unresolved. Preserve the existing database unchanged during reconciliation. Whether it can remain unchanged for deployment is undetermined.**

Database owner reported: scec_engagement_migrator. Potential write-capable roles: postgres, scec_engagement_migrator, pg_write_all_data. The latter is a built-in privilege role; login capability, memberships, effective object grants and actual app identity must be verified rather than inferred. Seven SCEC-related unit files exist, but enabled/active/write capability are separate questions. No connections at inspection is not proof of no writers. SSL/localhost listener and row_security=false on all 18 tables were reported. The synthetic schema also has RLS disabled on all its tables; that shared setting alone does not explain the mismatch or certify tenant isolation. No RLS or grant alteration is proposed as a blind remedy.

## Comparison evidence prepared

- `compare_schema.py`: deterministic named-table/column/constraint/index comparison; reports type/default/nullability/identity/generated changes, column order, RLS, missing/extra objects, exact name-only constraint changes and SQL definition text differences. It sorts named set-like collections to diagnose ordering but never silently rewrites SQL expressions or declares an independent deployment GO.
- `schema-comparer-tests.log`: seven executed focused tests passed, including collection ordering, column order, type/default/nullability/RLS changes, constraint rename, SQL literal whitespace preservation, missing index/extra table and duplicate-name refusal. These are tool tests, not production compatibility tests.
- `admin-reconcile-schema.py`: administrator-run read-only wrapper combining the existing inventory with comparison, PostgreSQL version/settings, enabled/active SCEC services, safe runtime/configured DB role identifiers and effective table grants/membership metadata. It emits no record bodies, passwords or service tokens and performs no migration, grant or service operation.
- Existing immutable synthetic image reports PostgreSQL **16.15 (Debian 16.15-1.pgdg13+2)**. No server was started for that binary-version check. Production version is pending the wrapper. Key ordering is canonically serialized; named collection order is checked separately; PostgreSQL rendering differences remain explicit review items.

Administrator command (no production data/config/service mutation):

```bash
umask 077
sudo python3 /home/catalystadmin/scec-issue15-recovery-metadata/admin-reconcile-schema.py > /home/catalystadmin/scec-issue15-recovery-metadata/reconciliation.json
```

This writes only a restricted metadata evidence file via shell redirection, not production data. After the administrator replies saved, retrieve it using the existing authorized SSH account. Review file hashes before root execution. All required comparison inputs are staged in that directory; expected input fingerprint is asserted. Tool hashes are in `reconciliation-tool-provenance.json`.

## Decision workflow after receiving exact metadata

1. Reproduce both canonical hashes and detect drift from the reported production fingerprint. Check server version, source SQL hash, search_path/encoding and named collection ordering before interpreting SQL text differences.
2. Review actual differences by table/column/constraint/index/RLS. Name-only differences and version rendering are not automatically safe: check application SQL, migrations, conflict handling and recovery tools for name dependencies. Changed type, nullability, defaults, predicates, uniqueness, checks, FKs or columns need explicit compatibility analysis.
3. Correlate enabled/active unit flags and handler dependencies with configured DSNs/roles and effective grants; distinguish OS process user, service principal and PostgreSQL login role. No inference from database owner or absent sessions. Map scheduled, administrative and external writers separately.
4. Reconcile actual alembic revision/history against source lineage and tested migration artifacts. Do not stamp, rerun or repair production migrations while investigating. Reproduce differences on a synthetic schema in isolation only after their exact definitions are known.
5. A recommendation to preserve the production DB unchanged requires compatible structure/semantics, understood migration history, verified writer/role boundaries and a tested backup/restore path. Any eventual change proposal must be a separately reviewed, reversible plan with owner approval; no destructive shortcut.

Identity, live tenant/security acceptance, privacy, backup and rollback gates remain open independently of schema matching. Same-person primary/deputy appointment does not supply independent approval. No v12.3/v13 feature development.
