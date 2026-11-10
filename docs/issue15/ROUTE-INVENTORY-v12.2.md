# Route and feature activation inventory — v12.2.0

Generated from FastAPI dependency trees at `baf31877c01e525b610a87830bb0165376ab16e3`. No live route mutations performed. Exact handlers, source lines, dependency source and module configuration variables are in `route-inventory.json`. Flags listed there are module-wide, not proof of per-route guard reachability.

| Method | Route | Guard | Class / activation | Source |
|---|---|---|---|---|
|GET|`/health`|handler-local / public|public health|`backend/app/main.py:21`|
|GET|`/v1/capabilities`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/main.py:25`|
|POST|`/v1/contracts/handoff/validate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/main.py:29`|
|GET|`/v1/contracts/canonical`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/main.py:36`|
|GET|`/v1/contracts/canonical/{model_name}/schema`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/main.py:40`|
|POST|`/v1/engagement/{kind}`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:53`|
|GET|`/v1/engagement/{kind}/{record_id}`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:58`|
|GET|`/v1/engagement/{kind}`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:62`|
|POST|`/v1/support/cases`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:69`|
|GET|`/v1/support/cases/{case_id}`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:73`|
|GET|`/v1/support/cases`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:77`|
|POST|`/v1/support/cases/{case_id}/transitions`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:81`|
|POST|`/v1/support/cases/{case_id}/feedback`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:86`|
|GET|`/v1/support/cases/{case_id}/history`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:91`|
|POST|`/v1/advisory/engagements`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:99`|
|GET|`/v1/advisory/engagements/{engagement_id}`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:103`|
|GET|`/v1/advisory/engagements`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:108`|
|POST|`/v1/advisory/engagements/{engagement_id}/approvals`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:117`|
|POST|`/v1/advisory/engagements/{engagement_id}/approvals/{approval_id}/decision`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:122`|
|POST|`/v1/advisory/engagements/{engagement_id}/transitions`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:127`|
|GET|`/v1/advisory/engagements/{engagement_id}/history`|service token + principal (bound mode only)|persistent; Stage 3 blocked|`backend/app/main.py:132`|
|GET|`/v1/human-auth/login`|handler-local / public|OIDC/session; gates 3–4 blocked|`backend/app/human_auth.py:114`|
|GET|`/v1/human-auth/callback`|handler-local / public|OIDC/session; gates 3–4 blocked|`backend/app/human_auth.py:137`|
|GET|`/v1/human-auth/session`|handler-local / public|OIDC/session; gates 3–4 blocked|`backend/app/human_auth.py:182`|
|POST|`/v1/human-auth/logout`|handler-local / public|OIDC/session; gates 3–4 blocked|`backend/app/human_auth.py:192`|
|POST|`/v1/human-auth/session/revoke-all`|handler-local / public|OIDC/session; gates 3–4 blocked|`backend/app/human_auth.py:206`|
|GET|`/v1/human-auth/authorization-check`|handler-local / public|OIDC/session; gates 3–4 blocked|`backend/app/human_auth.py:218`|
|GET|`/v1/intake/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/intake_v910.py:55`|
|POST|`/v1/intake/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/intake_v910.py:61`|
|POST|`/v1/intake/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/intake_v910.py:73`|
|GET|`/v1/community-intelligence/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feature_intelligence_v920.py:75`|
|POST|`/v1/community-intelligence/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feature_intelligence_v920.py:79`|
|POST|`/v1/community-intelligence/aggregate-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feature_intelligence_v920.py:83`|
|POST|`/v1/community-intelligence/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feature_intelligence_v920.py:96`|
|GET|`/v1/support-intelligence/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/support_intelligence_v930.py:72`|
|POST|`/v1/support-intelligence/case-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/support_intelligence_v930.py:76`|
|POST|`/v1/support-intelligence/summary-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/support_intelligence_v930.py:80`|
|POST|`/v1/support-intelligence/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/support_intelligence_v930.py:85`|
|GET|`/v1/institutional-intelligence/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_intelligence_v940.py:86`|
|POST|`/v1/institutional-intelligence/relationship-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_intelligence_v940.py:91`|
|POST|`/v1/institutional-intelligence/portfolio-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_intelligence_v940.py:96`|
|POST|`/v1/institutional-intelligence/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_intelligence_v940.py:106`|
|GET|`/v1/communications-intelligence/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communications_intelligence_v950.py:57`|
|POST|`/v1/communications-intelligence/plan-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communications_intelligence_v950.py:63`|
|POST|`/v1/communications-intelligence/audit-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communications_intelligence_v950.py:67`|
|POST|`/v1/communications-intelligence/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communications_intelligence_v950.py:76`|
|POST|`/v1/communications-intelligence/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communications_intelligence_v950.py:80`|
|GET|`/v1/engagement-analytics/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/engagement_analytics_v960.py:72`|
|POST|`/v1/engagement-analytics/report-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/engagement_analytics_v960.py:78`|
|POST|`/v1/engagement-analytics/funnel-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/engagement_analytics_v960.py:84`|
|POST|`/v1/engagement-analytics/export`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/engagement_analytics_v960.py:92`|
|POST|`/v1/engagement-analytics/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/engagement_analytics_v960.py:96`|
|GET|`/v1/privacy-governance/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_governance_v970.py:93`|
|POST|`/v1/privacy-governance/policy-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_governance_v970.py:98`|
|POST|`/v1/privacy-governance/rights-request-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_governance_v970.py:103`|
|POST|`/v1/privacy-governance/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_governance_v970.py:113`|
|POST|`/v1/privacy-governance/consent-commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_governance_v970.py:117`|
|POST|`/v1/privacy-governance/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_governance_v970.py:121`|
|GET|`/v1/federation-intelligence/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:66`|
|POST|`/v1/federation-intelligence/handoff-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:72`|
|POST|`/v1/federation-intelligence/compatibility-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:77`|
|POST|`/v1/federation-intelligence/token-exchange`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:86`|
|POST|`/v1/federation-intelligence/link-identity`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:89`|
|POST|`/v1/federation-intelligence/handoff-commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:92`|
|POST|`/v1/federation-intelligence/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/federation_intelligence_v980.py:95`|
|GET|`/v1/release-assurance/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:60`|
|POST|`/v1/release-assurance/assessment-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:65`|
|GET|`/v1/release-assurance/reliability-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:70`|
|POST|`/v1/release-assurance/enable-federation`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:78`|
|POST|`/v1/release-assurance/enable-deletion`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:78`|
|POST|`/v1/release-assurance/enable-outbound`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:78`|
|POST|`/v1/release-assurance/enable-writes`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:78`|
|POST|`/v1/release-assurance/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:78`|
|POST|`/v1/release-assurance/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/release_assurance_v990.py:78`|
|GET|`/v1/unified-platform/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:26`|
|GET|`/v1/unified-platform/catalog`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:29`|
|GET|`/v1/unified-platform/readiness`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:32`|
|POST|`/v1/unified-platform/consolidation-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:35`|
|POST|`/v1/unified-platform/enable-live`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:40`|
|POST|`/v1/unified-platform/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:40`|
|POST|`/v1/unified-platform/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/unified_v1000.py:40`|
|GET|`/v1/application-shell/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/application_shell_v1010.py:19`|
|GET|`/v1/application-shell/navigation`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/application_shell_v1010.py:23`|
|POST|`/v1/application-shell/enable-live`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/application_shell_v1010.py:27`|
|POST|`/v1/application-shell/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/application_shell_v1010.py:27`|
|GET|`/v1/identity-certification/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/identity_certification_v1020.py:68`|
|GET|`/v1/identity-certification/requirements`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/identity_certification_v1020.py:72`|
|POST|`/v1/identity-certification/enable-writes`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/identity_certification_v1020.py:78`|
|POST|`/v1/identity-certification/enable-login`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/identity_certification_v1020.py:78`|
|POST|`/v1/identity-certification/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/identity_certification_v1020.py:78`|
|POST|`/v1/identity-certification/certify`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/identity_certification_v1020.py:78`|
|GET|`/v1/tenant-authorization/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/tenant_authorization_v1030.py:50`|
|GET|`/v1/tenant-authorization/matrix`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/tenant_authorization_v1030.py:53`|
|POST|`/v1/tenant-authorization/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/tenant_authorization_v1030.py:57`|
|POST|`/v1/tenant-authorization/enable-live`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/tenant_authorization_v1030.py:57`|
|POST|`/v1/tenant-authorization/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/tenant_authorization_v1030.py:57`|
|POST|`/v1/tenant-authorization/certify`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/tenant_authorization_v1030.py:57`|
|GET|`/v1/transaction-foundation/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/transaction_foundation_v1040.py:86`|
|GET|`/v1/transaction-foundation/requirements`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/transaction_foundation_v1040.py:89`|
|POST|`/v1/transaction-foundation/enable-writes`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/transaction_foundation_v1040.py:93`|
|POST|`/v1/transaction-foundation/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/transaction_foundation_v1040.py:93`|
|POST|`/v1/transaction-foundation/certify`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/transaction_foundation_v1040.py:93`|
|POST|`/v1/transaction-foundation/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/transaction_foundation_v1040.py:93`|
|GET|`/v1/wordpress-intake-certification/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:80`|
|GET|`/v1/wordpress-intake-certification/requirements`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:86`|
|POST|`/v1/wordpress-intake-certification/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:90`|
|POST|`/v1/wordpress-intake-certification/forward`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:95`|
|POST|`/v1/wordpress-intake-certification/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:95`|
|POST|`/v1/wordpress-intake-certification/certify`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:95`|
|POST|`/v1/wordpress-intake-certification/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/wordpress_bridge_certification_v1050.py:95`|
|GET|`/v1/privacy-consent-retention/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:60`|
|GET|`/v1/privacy-consent-retention/policy-draft`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:66`|
|POST|`/v1/privacy-consent-retention/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:72`|
|POST|`/v1/privacy-consent-retention/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:77`|
|POST|`/v1/privacy-consent-retention/export`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:77`|
|POST|`/v1/privacy-consent-retention/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:77`|
|POST|`/v1/privacy-consent-retention/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:77`|
|POST|`/v1/privacy-consent-retention/approve`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/privacy_consent_retention_v1060.py:77`|
|GET|`/v1/delivery-infrastructure/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:73`|
|GET|`/v1/delivery-infrastructure/contracts`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:79`|
|POST|`/v1/delivery-infrastructure/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:86`|
|POST|`/v1/delivery-infrastructure/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|POST|`/v1/delivery-infrastructure/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|POST|`/v1/delivery-infrastructure/approve`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|POST|`/v1/delivery-infrastructure/retry`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|POST|`/v1/delivery-infrastructure/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|POST|`/v1/delivery-infrastructure/dispatch`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|POST|`/v1/delivery-infrastructure/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/delivery_infrastructure_v1070.py:91`|
|GET|`/v1/observability-reliability/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:72`|
|GET|`/v1/observability-reliability/contracts`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:78`|
|POST|`/v1/observability-reliability/assess`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:84`|
|POST|`/v1/observability-reliability/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|POST|`/v1/observability-reliability/create-incident`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|POST|`/v1/observability-reliability/restore`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|POST|`/v1/observability-reliability/recover`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|POST|`/v1/observability-reliability/retry`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|POST|`/v1/observability-reliability/alert`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|POST|`/v1/observability-reliability/collect`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/observability_reliability_v1080.py:89`|
|GET|`/v1/production-acceptance/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:88`|
|GET|`/v1/production-acceptance/gates`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:92`|
|POST|`/v1/production-acceptance/evidence-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:97`|
|POST|`/v1/production-acceptance/certify-live-gates`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|POST|`/v1/production-acceptance/promote`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|POST|`/v1/production-acceptance/enable-federation`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|POST|`/v1/production-acceptance/delete-records`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|POST|`/v1/production-acceptance/enable-human-login`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|POST|`/v1/production-acceptance/enable-outbound`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|POST|`/v1/production-acceptance/enable-production-writes`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/production_acceptance_v1090.py:102`|
|GET|`/v1/research-distribution/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:85`|
|POST|`/v1/research-distribution/manifest-preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:91`|
|POST|`/v1/research-distribution/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|POST|`/v1/research-distribution/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|POST|`/v1/research-distribution/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|POST|`/v1/research-distribution/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|POST|`/v1/research-distribution/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|POST|`/v1/research-distribution/syndicate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|POST|`/v1/research-distribution/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/research_distribution_v1100.py:96`|
|GET|`/v1/research-feeds/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:123`|
|POST|`/v1/research-feeds/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:128`|
|POST|`/v1/research-feeds/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|POST|`/v1/research-feeds/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|POST|`/v1/research-feeds/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|POST|`/v1/research-feeds/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|POST|`/v1/research-feeds/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|POST|`/v1/research-feeds/syndicate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|POST|`/v1/research-feeds/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/feed_serialization_v1110.py:133`|
|GET|`/v1/institutional-newsroom/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:105`|
|POST|`/v1/institutional-newsroom/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:110`|
|POST|`/v1/institutional-newsroom/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/syndicate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/release`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|POST|`/v1/institutional-newsroom/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/institutional_newsroom_v1120.py:115`|
|GET|`/v1/research-alerts/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:223`|
|POST|`/v1/research-alerts/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:231`|
|POST|`/v1/research-alerts/export-contacts`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/token-exchange`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/schedule`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/syndicate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|POST|`/v1/research-alerts/subscribe`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/newsletter_alerts_v1130.py:237`|
|GET|`/v1/media-relations/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:98`|
|POST|`/v1/media-relations/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:103`|
|POST|`/v1/media-relations/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/export-contacts`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/schedule`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|POST|`/v1/media-relations/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/media_relations_v1140.py:109`|
|GET|`/v1/citation-discovery/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:167`|
|POST|`/v1/citation-discovery/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:172`|
|POST|`/v1/citation-discovery/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|POST|`/v1/citation-discovery/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|POST|`/v1/citation-discovery/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|POST|`/v1/citation-discovery/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|POST|`/v1/citation-discovery/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|POST|`/v1/citation-discovery/index`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|POST|`/v1/citation-discovery/register`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/citation_discovery_v1150.py:178`|
|GET|`/v1/events/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:137`|
|POST|`/v1/events/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:142`|
|POST|`/v1/events/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/schedule`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/write-calendar`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/broadcast`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/invite`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|POST|`/v1/events/register`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/events_v1160.py:148`|
|GET|`/v1/partnerships/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:109`|
|POST|`/v1/partnerships/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:114`|
|POST|`/v1/partnerships/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/link-identity`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/token-exchange`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/deliver`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|POST|`/v1/partnerships/export`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/partnerships_v1170.py:120`|
|GET|`/v1/research-embeds/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:136`|
|POST|`/v1/research-embeds/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:141`|
|POST|`/v1/research-embeds/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|POST|`/v1/research-embeds/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|POST|`/v1/research-embeds/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|POST|`/v1/research-embeds/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|POST|`/v1/research-embeds/enable-cors`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|POST|`/v1/research-embeds/serve-public`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|POST|`/v1/research-embeds/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/embeds_v1180.py:150`|
|GET|`/v1/audience-analytics/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:94`|
|POST|`/v1/audience-analytics/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:99`|
|POST|`/v1/audience-analytics/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/export-identities`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/collect`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|POST|`/v1/audience-analytics/track`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/audience_v1190.py:105`|
|GET|`/v1/communication-objects/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:132`|
|POST|`/v1/communication-objects/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:137`|
|POST|`/v1/communication-objects/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:143`|
|POST|`/v1/communication-objects/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:143`|
|POST|`/v1/communication-objects/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:143`|
|POST|`/v1/communication-objects/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:143`|
|POST|`/v1/communication-objects/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:143`|
|POST|`/v1/communication-objects/commit`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/communication_objects_v1200.py:143`|
|GET|`/v1/editorial-planning/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:137`|
|POST|`/v1/editorial-planning/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:142`|
|POST|`/v1/editorial-planning/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/notify`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/write-calendar`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/start-cron`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|POST|`/v1/editorial-planning/schedule`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/editorial_planning_v1210.py:148`|
|GET|`/v1/campaign-composer/status`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:134`|
|POST|`/v1/campaign-composer/preview`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:139`|
|POST|`/v1/campaign-composer/federate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/delete`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/activate`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/enqueue`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/schedule`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/export-recipients`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/subscribe`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/publish`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
|POST|`/v1/campaign-composer/send`|service token + principal (bound mode only)|synthetic/contract; disabled by default, reviewed phase only|`backend/app/campaigns_v1220.py:145`|
