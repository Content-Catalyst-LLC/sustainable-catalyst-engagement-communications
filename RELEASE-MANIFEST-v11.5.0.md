# v11.5.0 — Academic citation and discovery staging

Baseline: v11.4.0, `2c803dcdb1216ef2cd55136b3cc3ba14cb2f7f74`.

Adds an existing-service router at `/v1/citation-discovery`: authenticated status and POST preview; default-off `SCEC_CITATION_STAGING_ENABLED=0`. Requires bound service identity, allowlisted tenant and administrator role. Every dangerous runtime flag denies access. No human login, persistence, lookup, outbound transport, indexing registration, publication, deletion, federation or token exchange. All seven production acceptance gates remain pending.

The strict synthetic journal-article fixture contains an opaque reference, revision, title, ordered synthetic authors, year, canonical HTTPS URL, explicit provenance references and optional supplied identifiers. Extra fields, cross-tenant children, duplicate authors/sources/relations, unsupported types, control characters and unprovenanced notices are rejected. This is a bounded fixture contract, not a general PII detector or a claim that arbitrary user input is anonymous.

Exports are BibTeX, RIS, CSL-JSON and schema.org JSON-LD previews. No identifier is invented when DOI is absent. BibTeX escapes control syntax and groups literal author names; RIS rejects line injection. JSON outputs are structured data, not executable HTML or safe-to-inline script content. Canonical URLs are never fetched; hostname checks do not resolve DNS or certify ownership. No browser rendering or public embed endpoint is introduced.

Correction, retraction and update notices remain explicit, source-linked sidecar relations in the evidence envelope. They are not silently inferred, collapsed into a publication status, or embedded into citation formats that cannot faithfully represent them. Consumers must preserve the envelope and notices with exports. ROR metadata is preserved in the fixture; it does not imply an author affiliation or organizational endorsement.

Identifier limits and primary references:

- [ORCID identifier structure](https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier): format and MOD 11-2 checksum only; no registration, ownership or author matching check.
- [Crossref DOI matching guidance](https://www.crossref.org/blog/dois-and-matching-regular-expressions/): conservative syntax subset; some historical DOIs are intentionally rejected. A syntax match proves neither registration nor publication authenticity.
- [ROR FAQ](https://ror.org/about/faqs/): canonical URL shape with nine lowercase alphanumeric characters only; checksum, existence and institutional facts are **not** verified.

Evidence hashes cover normalized source references, ordered authors, revision, explicit notices, outputs and authoritative disabled states. Newline/control rejection prevents RIS record injection. Synthetic examples and supplied test identifiers are fixtures, not newly assigned persistent identifiers.

No dependencies, frontend, WordPress bridge, historical migration or database configuration changes. Five WordPress destinations remain preserved. Full Mac and isolated Contabo regression, preflight, exact-source hashes, protected-file comparison, loopback HTTP negative checks and owned-process shutdown must pass before v11.6 begins. See deployment/V1150-DEPLOY.md for reproducible commands. Production remains uncertified and untouched.
