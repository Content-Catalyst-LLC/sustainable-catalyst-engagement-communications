# v11 staging readiness and v12 interface handoff

**Production NOT CERTIFIED.** This is an offline/source and isolated-staging program, not a live production acceptance program. Draft release branches are pushed for review; no PR is merged into main. Main remains the preserved v11.2 baseline. Five WordPress destinations, existing services, credentials, databases, Docker, proxies and public URLs are outside this program's changes.

## Evidence already closed before this candidate

| Release | Exact source commit | Full Mac / Contabo tests | Status |
|---|---|---|---|
|11.2|61543658d111eac2993abc86206dc8a8479dc562|571/571 historical accepted evidence; not rerun in this session|Missing HTTP and port8841 shutdown evidence independently closed|
|11.3|12f58a3ad3ac1779b0045f1cb36acdcdcc74a920|674/674|Isolated staging closed; PR7|
|11.4|2c803dcdb1216ef2cd55136b3cc3ba14cb2f7f74|711/711|Isolated staging closed; PR8|
|11.5|f58b4a7d43908c998c5b232c311cd30eda4dc00d|764/764|Isolated staging closed; PR9|
|11.6|d1a640e32dbe349c2f469af93e3f52a902a89190|804/804|Isolated staging closed; PR10|
|11.7|74bfb048570f9d26411091ede2340e5a1cd657af|839/839|Isolated staging closed; PR11|
|11.8|e0452613d5cee1f48fe20fa8a0bf6472517d5bf3|883/883|Isolated staging closed; PR12|

v11.9 closure must be recorded against its final pushed SHA with actual test counts, not a predicted count in this source document. Raw logs, certificate JSON, complete ZIP/checksum audits and shutdown evidence are retained in the owner-facing certification package and GitHub issue3. A passing source report alone does not close staging.

## Compatibility and reuse

| Existing interface | Integration evidence / adapter requirement |
|---|---|
|v11.0 DistributionPreview/preview|Source fingerprint preserved inside v11.7 package manifests. Production review gate remains false; historical response lacks production_certified.|
|v11.1 FeedPreview/render|Deterministic synthetic feed serialization; no public serving. Historical previews can include unreviewed metadata; publication remains false.|
|v11.2 NewsroomPreview/assess|Source-linked announcements and review decisions; no persistent editorial history or publication.|
|v11.3 AlertPreview/compose|Synthetic preferences only; consent/review suppression; no actual recipients or subscription records.|
|v11.4 PressPackage/assess|Embargo/review/suppression-aware press preview; no contact directory or sending.|
|v11.5 Publication/export|Conservative DOI syntax, ORCID checksum and ROR shape only; no identifier registration/existence certification. Notices are sidecars.|
|v11.6 Event/preview_event|Explicit offsets checked against host IANA data, UTC calendar preview. No persistent transition history or calendar client.|
|v11.7 PartnerPackage/plan|Strict synthetic policies; unknown/restricted rights denied; no cross-tenant export or institutional trust establishment.|
|v11.8 Embed/render_embed|Versioned contract, exact operator origin policy, withholding and escaped markup. No browser renderer or public CORS.|
|v11.9 AudienceBatch/aggregate_audience|Synthetic deduplication/distinct readers/whole-table small-cell suppression. No real tracking, causal analysis or cross-query privacy guarantee.|

Cross-release tests invoke these functions using a common fixture and block socket connects. This is a tested contract chain, not a deployed orchestration service. Future adapters must retain each module's provenance, revision, safety state and notices, enforce their own strict input models, and never reinterpret preview approval as authorization to publish or deliver. Historical permissive boolean coercion is not adopted by new strict fixture contracts. Event integer sequence and other string revisions require explicit typed adapters, not silent coercion.

## Reproduction, protection and recovery

Install backend/requirements-lock-v1130.txt in a new venv, run all backend tests and certification/certify.py without --live. Compare the protected16 files against the predecessor. Verify the current checksum manifest and actual ZIP members. See deployment/V1190-DEPLOY.md for exact staging steps and tools/verify_staging.py for sanitized temporary loopback checks.

The owner approved user-owned Contabo staging because /opt creation required unavailable sudo. Each release has its own /home/catalystadmin/scec-vNNNN/repository, detached exact SHA and clean checkout. Port availability is checked before launch; only the newly owned process is stopped and its listener is checked afterward. No production schema/proxy/container changes occur. Rollback is termination of that temporary process and retention of predecessor source/evidence, not a production database restore.

One inherited Starlette/AnyIO deprecation warning remains; pinned dependencies pass on Mac Python3.13 and Contabo Python3.12. No new runtime dependency was introduced. A fresh venv was installed for v11.3 on Mac and reused with the unchanged exact lock for later Mac runs; every Contabo release used a fresh venv. This is not evidence for untested Python/OS combinations.

## Production blockers remain mandatory

- public_https_dns_tls
- wordpress_public_launcher_acceptance
- authenticated_human_session
- csrf_revocation_session_expiry
- live_tenant_isolation_roles
- privacy_retention_policy
- staged_persistence_write_certification

No live human login, PII ingestion, actual subscriptions, outbound messaging, publication, deletion, federation/token exchange, cron/transport workers or analytics collection was enabled. These gates require a separately authorized and evidenced production program. Review/merge is separate; nothing here authorizes deployment.

## Next roadmap

Owner confirmed the simulation-only scopes in issues4 and5. After v11.9 staging closes, review issue4 against this concrete interface matrix before implementing v12.0. Keep v12.0–v12.9 and then v13.0–v13.9 sequential, separately tested, packaged, source-pinned and isolated-staging certified. No successor may bypass an unresolved predecessor security/test gate.
