# v11.7.0 — Partnership and institutional distribution staging

Baseline v11.6.0: `d1a640e32dbe349c2f469af93e3f52a902a89190`.

Default-off `SCEC_PARTNERS_STAGING_ENABLED=0`; `/v1/partnerships/status` and POST `/preview` require bound service identity, allowlisted tenant and administrator role. All dangerous runtime flags deny access. Seven live production gates remain pending.

Synthetic partner profiles use opaque institution/partner references and academic/research/policy/community classifications. No contact PII, external credentials, account linking or real institution directory is ingested. Package artifacts preserve revision, object type, source references, licence and access classification. Nested fixture tenants must match; duplicates are rejected.

Reuses v11.0 DistributionPreview and its deterministic source manifest, without changing the historical interface or release identity. New strict review gates are checked independently. Partner institutional/rights review, artifact rights/editorial/privacy/source/distribution reviews, licence acceptance, access classification and suppression all constrain eligibility. Unknown licences fail closed even if a profile lists them; restricted content or licences never route. Internal artifacts can only be planned inside the package institution; external institution plans require public classification. A single denied artifact denies the whole package for that partner.

Eligibility means only a synthetic planning decision; licence labels and asserted reviews do not verify legal compliance or grant redistribution permission. The source manifest and policy evidence remain within the authenticated originating tenant. There is no cross-tenant export endpoint, payload transfer, federation call, token exchange, identity linking or delivery. All live-operation routes explicitly return503 even for a reviewed administrator.

Normalized evidence hashes include package revision, policies, source manifests and decisions. Frontend, WordPress destinations, migrations, database and dependencies remain unchanged. See deployment/V1170-DEPLOY.md. v11.8 is gated on full Mac/Contabo tests, preflight, protected hashes, complete archive checks, exact-commit loopback safety checks and clean owned-process shutdown.
