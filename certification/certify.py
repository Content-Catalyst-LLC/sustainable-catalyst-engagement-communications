#!/usr/bin/env python3
"""Non-mutating v8.9.0 certification. Never handles keys or customer data."""
import argparse, json, os, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def check_source():
    data={}
    manifest=json.loads((ROOT/'RELEASE-MANIFEST.json').read_text())
    data['release_manifest_890']=manifest.get('version') in ('8.9.0','9.0.0','9.1.0','9.2.0','9.3.0','9.4.0','9.5.0','9.6.0','9.7.0','9.8.0','9.9.0','10.0.0','10.1.0','10.2.0','10.3.0','10.4.0','10.5.0','10.6.0','10.7.0','10.8.0','10.9.0','11.0.0','11.1.0','11.2.0','11.3.0','11.4.0','11.5.0','11.6.0','11.7.0','11.8.0','11.9.0','12.0.0','12.1.0','12.2.0','12.3.0','12.4.0','12.5.0')
    data['database_contract_unchanged']=manifest.get('schema_revision')=='850_001'
    data['writes_disabled_contract']=manifest.get('production_writes_default')=='disabled'
    data['independent_web_present']=all((ROOT/p).exists() for p in ('frontend/index.html','frontend/compose.yaml','frontend/nginx.conf'))
    data['web_local_only_compose']='127.0.0.1:8097:80' in (ROOT/'frontend/compose.yaml').read_text()
    html=(ROOT/'frontend/index.html').read_text()
    data['read_only_web_disclosure']='READ-ONLY PREVIEW' in html and 'NOT LIVE RECORDS' in html
    nginx=(ROOT/'frontend/nginx.conf').read_text()
    data['security_headers']='X-Frame-Options DENY' in nginx and 'Content-Security-Policy' in nginx and "connect-src 'none'" in nginx
    plugin=(ROOT/'wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php').read_text()
    data['wordpress_bridge_present']='sc_engagement_communications' in plugin
    data['wordpress_five_existing_links']=all("array('"+label+"'," in plugin for label in ['Contact','Feedback','Feature Suggestions','Channel','Support'])
    data['wordpress_no_forms_or_redirects']=not any(x in plugin for x in ['wp_insert_post(', 'wp_delete_post(', 'wp_redirect(', 'wp_remote_post('])
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from app.wordpress_bridge_certification_v1050 import source_report
    data.update({'v1050_'+k: v for k, v in source_report(ROOT).items()})
    from app.privacy_consent_retention_v1060 import RETENTION, PURPOSE, GATES
    data['v1060_all_five_channels']=set(RETENTION)==set(PURPOSE)=={'contact','feedback','feature-suggestions','channel','support'}
    data['v1060_draft_retention_only']=all(isinstance(v,int) and 1 <= v <= 365 for v in RETENTION.values())
    data['v1060_privacy_acceptance_pending']='production_privacy_acceptance' in GATES
    data['v1060_no_bridge_mutation']=data['v1050_no_wordpress_mutation'] and data['v1050_no_remote_proxy']
    from app.delivery_infrastructure_v1070 import GATES as DELIVERY_GATES, CHANNELS as DELIVERY_CHANNELS, RETRY_SECONDS
    data['v1070_no_transport_adapters']=manifest.get('outbound_messaging_enabled') is False and manifest.get('delivery_infrastructure_mode','').startswith('synthetic-')
    data['v1070_review_gates_defined']='human_dispatch_approval' in DELIVERY_GATES and 'production_acceptance' in DELIVERY_GATES
    data['v1070_delivery_channels']=set(DELIVERY_CHANNELS)=={'email','in-app','sms'}
    data['v1070_retry_schedule_preview']=RETRY_SECONDS==(60,300,1800)
    data['v1070_no_wordpress_mutation']=data['v1050_no_wordpress_mutation']
    from app.observability_reliability_v1080 import FAILURES, LIVE_GATES, RETRY_SECONDS as RELIABILITY_RETRY
    data['v1080_failure_classification']=set(FAILURES)=={'none','transient-network','timeout','rate-limited','dependency-down','invalid-contract','authorization-denied','integrity-failure'}
    data['v1080_no_live_recovery']=manifest.get('observability_reliability_mode')=='synthetic-evidence-only-no-monitoring-alerting-recovery-or-mutation'
    data['v1080_approval_gates']=set(['alert_routing_review','backup_restore_exercise','production_acceptance']).issubset(LIVE_GATES)
    data['v1080_retry_preview_only']=RELIABILITY_RETRY==(60,300,1800)
    data['v1080_five_pages_unchanged']=data['v1050_no_wordpress_mutation'] and data['wordpress_five_existing_links']
    from app.production_acceptance_v1090 import GATES as V1090_GATES, RELEASES, PROTECTED, acceptance_report, BLOCKED_ACTIONS
    pending=('public_https_dns_tls','wordpress_public_launcher_acceptance','authenticated_human_session','csrf_revocation_session_expiry','live_tenant_isolation_roles','privacy_retention_policy','staged_persistence_write_certification')
    state=acceptance_report(source_preflight_passed=True)
    data['v1090_all_seven_live_gates_pending']=V1090_GATES==pending and state['gates_not_certified']==list(pending) and not state['live_checks']
    data['v1090_all_ten_release_lineage']=RELEASES==tuple(f'10.{i}.0' for i in range(10))
    data['v1090_five_wordpress_destinations_preserved']=set(PROTECTED)=={'contact','feedback','feature-suggestions','channel','support'} and data['v1050_no_wordpress_mutation'] and data['wordpress_five_existing_links']
    data['v1090_no_automatic_production_promotion']=all(state.get(x) is False for x in ('production_certified','production_writes_enabled','outbound_communications_enabled','human_login_enabled','deletion_enabled','federation_enabled','automatic_promotion_enabled','production_approval_granted'))
    data['v1090_production_actions_blocked']=len(BLOCKED_ACTIONS)==7 and manifest.get('production_acceptance_mode')=='source-and-staging-evidence-only-no-live-gates-no-activation'
    from app.research_distribution_v1100 import (DISTRIBUTION_TARGETS, OBJECT_TYPES, REQUIRED_REVIEW,
        BLOCKED_ACTIONS as DISTRIBUTION_BLOCKED, DistributionPreview, preview as distribution_preview)
    from uuid import uuid4
    test=DistributionPreview(object_ref='synthetic-research',revision='v1',object_kind='research-article',targets=['rss'],source_refs=['source-123'],rights_basis='open-license',editorial_reviewed=True,privacy_reviewed=True,source_integrity_reviewed=True,distribution_approved=True)
    assessment=distribution_preview(test,str(uuid4()))
    data['v1100_target_contracts']=set(DISTRIBUTION_TARGETS)=={'rss','atom','json-feed','institutional-newsroom','newsletter','citation-index'} and len(OBJECT_TYPES)==5
    data['v1100_review_gates']=set(REQUIRED_REVIEW)==set(assessment['review_gates']) and assessment['review_gates']['production_acceptance'] is False
    data['v1100_no_actual_distribution']=all(assessment[k] is False for k in ('publication_authorized','actual_publication_enabled','actual_syndication_enabled','outbound_communications_enabled','persisted','live_sources_fetched','federation_enabled')) and len(DISTRIBUTION_BLOCKED)==7
    data['v1100_seven_live_gates_pending']=assessment['live_acceptance_gates_pending']==list(pending)
    data['v1100_wordpress_preserved']=data['v1090_five_wordpress_destinations_preserved'] and data['v1050_no_wordpress_mutation']
    data['v1100_manifest_fail_closed']=manifest.get('research_distribution_mode')=='synthetic-provenance-manifest-preview-no-fetch-publishing-syndication-transport-persistence' and manifest.get('outbound_messaging_enabled') is False and manifest.get('production_writes_enabled') is False
    from app.feed_serialization_v1110 import FORMATS, BLOCKED_ACTIONS as FEED_BLOCKED, FeedPreview, FeedEntry, render
    from datetime import datetime, timezone
    sample=FeedEntry(object_ref='research-123',revision='v1',title='Synthetic title',summary='Synthetic summary',canonical_url='https://example.org/research/123',updated_at=datetime(2026,10,17,tzinfo=timezone.utc),source_refs=['source-123'])
    test_feed=FeedPreview(format='rss',feed_title='Synthetic feed',feed_description='Synthetic preview',home_url='https://example.org/',feed_url='https://example.org/feed.xml',entries=[sample])
    preview=render(test_feed,str(uuid4()))
    data['v1110_supported_formats']=FORMATS==('rss','atom','json-feed')
    data['v1110_no_live_publication']=all(preview[k] is False for k in ('publication_authorized','actual_syndication_enabled','outbound_communications_enabled','persisted','source_fetch_performed','federation_enabled','production_certified')) and len(FEED_BLOCKED)==7
    data['v1110_feed_serialization']=preview['media_type']=='application/rss+xml' and '<rss' in preview['content_preview']
    data['v1110_live_gates_pending']=preview['live_acceptance_gates_pending']==list(pending)
    data['v1110_five_wordpress_destinations_preserved']=data['v1100_wordpress_preserved']
    data['v1110_mode_disabled']=manifest.get('feed_mode')=='synthetic-serialization-preview-only-no-public-routes-or-delivery'
    from app.institutional_newsroom_v1120 import (ANNOUNCEMENT_KINDS,STATES,REVIEW_GATES,BLOCKED_ACTIONS as NEWS_BLOCKED,NewsroomEntry,NewsroomPreview,assess as newsroom_assess)
    news=NewsroomEntry(announcement_ref='synthetic-release',revision='v1',kind='research-release',headline='Synthetic headline',summary='Synthetic summary',canonical_url='https://example.org/news/research',updated_at=datetime(2026,10,17,tzinfo=timezone.utc),source_refs=['source-123'],rights_reviewed=True,editorial_reviewed=True,source_integrity_reviewed=True,privacy_reviewed=True,institutional_approved=True)
    preview=newsroom_assess(NewsroomPreview(newsroom_title='Synthetic',newsroom_url='https://example.org/news',entries=[news]),str(uuid4()))
    data['v1120_newsroom_content_contracts']=len(ANNOUNCEMENT_KINDS)==5 and len(STATES)==4 and len(REVIEW_GATES)==6
    data['v1120_human_review_cannot_publish']=preview['entries'][0]['editorial_review_complete'] and not preview['entries'][0]['publication_authorized']
    data['v1120_publication_blocked']=len(NEWS_BLOCKED)==8 and all(preview[k] is False for k in ('actual_publication_enabled','outbound_communications_enabled','persisted','source_fetch_performed','federation_enabled','human_login_enabled','deletion_enabled','production_certified'))
    data['v1120_seven_gates_pending']=preview['live_acceptance_gates_pending']==list(pending)
    data['v1120_wordpress_preserved']=data['v1110_five_wordpress_destinations_preserved']
    data['v1120_manifest_staging_only']=manifest.get('newsroom_mode')=='synthetic-editorial-release-history-preview-no-publication-transports-writes-or-federation'
    from app.newsletter_alerts_v1130 import TOPICS, FREQUENCIES, CHANNELS, BLOCKED_ACTIONS as ALERT_BLOCKED, SubscriptionPreference, ResearchAlert, AlertPreview, compose
    org = str(uuid4())
    pref = SubscriptionPreference(synthetic=True, organization_id=org, subscriber_ref='synthetic:'+str(uuid4()), topics=['methods-data'], channels=['email'])
    alert = ResearchAlert(synthetic=True, organization_id=org, object_ref='research:synthetic', revision='r1', headline='Synthetic review', summary='Synthetic source summary', source_refs=['source:synthetic'], topics=['methods-data'])
    result = compose(AlertPreview(alert=alert, preferences=[pref]), org)
    data['v1130_preference_contracts'] = len(TOPICS)==8 and FREQUENCIES==('immediate','daily','weekly','monthly') and CHANNELS==('email','in-app')
    data['v1130_consent_optout_fail_closed'] = result['preview_eligible_count']==0 and pref.consent is False and pref.state=='opted-out'
    data['v1130_no_production_side_effects'] = len(ALERT_BLOCKED)==11 and all(result[k] is False for k in ('publication_authorized','subscription_activation_enabled','outbound_communications_enabled','scheduled_delivery_enabled','persisted','source_fetch_performed','human_login_enabled','deletion_enabled','federation_enabled','token_exchange_enabled','production_writes_enabled','production_certified'))
    data['v1130_seven_gates_pending'] = result['live_acceptance_gates_pending']==list(pending)
    data['v1130_manifest_preview_only'] = manifest.get('newsletter_alerts_mode')=='offline-synthetic-preferences-segmentation-composition-no-subscribers-persistence-transport-or-publication'
    data['v1130_wordpress_preserved'] = data['v1120_wordpress_preserved']
    from app.media_relations_v1140 import OutletClassification, PressPackage, assess as press_assess
    outlet=OutletClassification(synthetic=True,organization_id=org,outlet_ref='synthetic:'+str(uuid4()),kind='academic',topics=['methods'])
    package=PressPackage(synthetic=True,organization_id=org,package_ref='press:synthetic',revision='r1',headline='Synthetic brief',pitch='Synthetic editorial pitch',source_refs=['source:synthetic'],spokesperson_ref='synthetic:'+str(uuid4()),as_of=datetime(2026,10,27,tzinfo=timezone.utc),outlets=[outlet])
    press=press_assess(package,org)
    data['v1140_reviews_fail_closed']=press['pitch_preview'] is None and not press['eligible_synthetic_outlets']
    data['v1140_no_delivery']=all(press[k] is False for k in ('production_certified','production_writes_enabled','actual_publication_enabled','outbound_communications_enabled','scheduled_delivery_enabled','persisted','federation_enabled'))
    data['v1140_gates_and_mode']=press['live_acceptance_gates_pending']==list(pending) and manifest.get('media_relations_mode')=='synthetic-classification-embargo-press-preview-no-contact-pii-or-delivery'
    from app.citation_discovery_v1150 import Author, Publication, export as citation_export
    publication=Publication(synthetic=True,organization_id=org,object_ref='citation:synthetic',revision='r1',title='Synthetic methods fixture',authors=[Author(synthetic=True,organization_id=org,name='Synthetic Author')],year=2026,canonical_url='https://example.org/research',source_refs=['source:synthetic'])
    citation=citation_export(publication,org)
    data['v1150_missing_doi_not_invented']='DOI' not in citation['exports']['csl_json'] and 'identifier' not in citation['exports']['schema_org_jsonld']
    data['v1150_no_indexing_or_writes']=citation['indexing_registration_enabled'] is False and all(citation[k] is False for k in ('production_certified','production_writes_enabled','actual_publication_enabled','outbound_communications_enabled','persisted'))
    data['v1150_gates_and_mode']=citation['live_acceptance_gates_pending']==list(pending) and manifest.get('citation_discovery_mode')=='offline-synthetic-citation-exports-no-indexing-or-registration'
    from app.events_v1160 import Event, Speaker, preview_event
    event=Event(synthetic=True,organization_id=org,event_ref='event:synthetic',revision=0,kind='webinar',title='Synthetic event',description='Synthetic fixture',canonical_url='https://example.org/event',starts_at='2026-11-01T12:00:00Z',ends_at='2026-11-01T13:00:00Z',updated_at='2026-10-27T00:00:00Z',timezone_name='UTC',speakers=[Speaker(synthetic=True,organization_id=org,speaker_ref='synthetic:'+str(uuid4()),attribution='Synthetic Speaker')],source_refs=['source:fixture'])
    event_result=preview_event(event,org)
    data['v1160_unreviewed_calendar_withheld']=event_result['ics_preview'] is None
    data['v1160_no_registration_or_writes']=all(event_result[k] is False for k in ('production_certified','production_writes_enabled','actual_publication_enabled','invitations_enabled','calendar_writes_enabled','registration_capture_enabled','persisted'))
    data['v1160_gates_and_mode']=event_result['live_acceptance_gates_pending']==list(pending) and manifest.get('events_mode')=='offline-synthetic-event-calendar-preview-no-registration-or-invitations'
    from app.partnerships_v1170 import Artifact, Partner, PartnerPackage, plan
    artifact=Artifact(synthetic=True,organization_id=org,object_ref='object:fixture',revision='r1',object_kind='publication',source_refs=['source:fixture'])
    partner=Partner(synthetic=True,organization_id=org,partner_ref='partner:fixture',institution_ref='institution:other',kind='academic',accepted_licenses=['cc-by'],allowed_classifications=['public'])
    partner_result=plan(PartnerPackage(synthetic=True,organization_id=org,package_ref='package:fixture',revision='r1',institution_ref='institution:owner',artifacts=[artifact],partners=[partner]),org)
    data['v1170_unreviewed_routing_denied']=partner_result['routing_decisions'][0]['eligible_for_synthetic_plan_only'] is False
    data['v1170_no_export_or_federation']=all(partner_result[k] is False for k in ('production_certified','production_writes_enabled','data_exported','federation_authorized','partner_delivery_enabled','persisted'))
    data['v1170_gates_and_mode']=partner_result['live_acceptance_gates_pending']==list(pending) and manifest.get('partnerships_mode')=='offline-synthetic-partner-routing-no-export-or-federation'
    from app.embeds_v1180 import Embed, render_embed
    embed=Embed(synthetic=True,organization_id=org,object_ref='embed:fixture',revision='r1',title='Synthetic title',summary='Synthetic summary',canonical_url='https://example.org/source',requested_origin='https://example.org',source_refs=['source:fixture'],updated_at='2026-10-26T00:00:00Z',expires_at='2026-10-28T00:00:00Z',as_of='2026-10-27T00:00:00Z')
    embed_result=render_embed(embed,org,['https://example.org'])
    data['v1180_unreviewed_embed_withheld']=embed_result['content'] is None and embed_result['html_fragment_preview'] is None
    data['v1180_no_public_serving_or_writes']=all(embed_result[k] is False for k in ('production_certified','production_writes_enabled','public_embed_serving_enabled','cors_enabled','remote_resources_enabled','persisted'))
    data['v1180_gates_and_mode']=embed_result['live_acceptance_gates_pending']==list(pending) and manifest.get('embeds_mode')=='offline-versioned-synthetic-embed-contract-no-public-serving-or-cors'
    from app.audience_v1190 import AudienceEvent, MetricSource, AudienceBatch, aggregate_audience
    metric=AudienceEvent(synthetic=True,organization_id=org,event_ref='synthetic:'+str(uuid4()),reader_ref='synthetic:'+str(uuid4()),object_ref='object:fixture',revision='r1',channel='embed',kind='view',occurred_day='2026-10-27',source_ref='source:fixture')
    audience=aggregate_audience(AudienceBatch(synthetic=True,organization_id=org,events=[metric],sources=[MetricSource(synthetic=True,organization_id=org,source_ref='source:fixture',edition='fixture-r1')]),org)
    data['v1190_small_cohort_suppressed']=audience['rows'] is None and audience['suppression_applied'] is True
    data['v1190_no_tracking_or_writes']=all(audience[k] is False for k in ('production_certified','production_writes_enabled','tracking_enabled','identity_export_enabled','persisted'))
    data['v1190_gates_and_mode']=audience['live_acceptance_gates_pending']==list(pending) and manifest.get('audience_mode')=='offline-synthetic-deduplicated-suppressed-aggregate-no-tracking'
    from app.communication_objects_v1200 import make_node, CommunicationObject, preview_object
    root_distribution=distribution_preview(test,org)
    evidence=make_node(synthetic=True,organization_id=org,node_ref='node:research',kind='research',research_ref=test.object_ref,research_revision=test.revision,artifact_ref=test.object_ref,artifact_revision=test.revision,source_release='11.0.0',source_hash_kind='source-manifest',source_digest=root_distribution['manifest_sha256'],source_refs=tuple(test.source_refs))
    canonical=preview_object(CommunicationObject(synthetic=True,organization_id=org,communication_ref='communication:fixture',revision='r1',root_node_ref=evidence.node_ref,nodes=(evidence,)),org)
    data['v1200_typed_hash_lineage']=canonical['object']['nodes'][0]['source_digest']==root_distribution['manifest_sha256'] and canonical['immutable_fixture_contract'] is True
    data['v1200_no_attestation_or_writes']=all(canonical[k] is False for k in ('production_certified','production_writes_enabled','source_digests_independently_verified','persisted'))
    data['v1200_gates_and_mode']=canonical['live_acceptance_gates_pending']==list(pending) and manifest.get('communication_objects_mode')=='frozen-synthetic-lineage-integrity-no-external-attestation-or-writes'
    from app.editorial_planning_v1210 import LaunchWindow, EditorialPlan, simulate_plan
    from app.communication_objects_v1200 import EvidencePointer
    canonical_fixture=CommunicationObject(synthetic=True,organization_id=org,communication_ref='communication:fixture',revision='r1',root_node_ref=evidence.node_ref,nodes=(evidence,))
    launch=LaunchWindow(synthetic=True,organization_id=org,window_ref='window:fixture',evidence=EvidencePointer(synthetic=True,organization_id=org,node_ref=evidence.node_ref,evidence_sha256=evidence.evidence_sha256),starts_at='2026-11-01T12:00:00Z',ends_at='2026-11-01T13:00:00Z',timezone_name='UTC')
    calendar=simulate_plan(EditorialPlan(synthetic=True,organization_id=org,plan_ref='plan:fixture',revision='r1',communication=canonical_fixture,communication_sha256=canonical['sha256'],as_of='2026-10-27T00:00:00Z',windows=(launch,)),org)
    data['v1210_missing_reviews_deny']=calendar['windows'][0]['eligible_for_plan_only'] is False
    data['v1210_no_calendar_or_writes']=all(calendar[k] is False for k in ('production_certified','production_writes_enabled','cron_enabled','calendar_writes_enabled','notifications_enabled','persisted'))
    data['v1210_gates_and_mode']=calendar['live_acceptance_gates_pending']==list(pending) and manifest.get('editorial_planning_mode')=='offline-evidence-bound-calendar-no-cron-or-writes'
    from app.campaigns_v1220 import StrictEntry, StrictDistribution, Campaign, compose_campaign
    entry=StrictEntry(announcement_ref=test.object_ref,revision=test.revision,kind='research-release',headline='Synthetic research headline',summary='Synthetic summary',canonical_url='https://example.org/research',updated_at='2026-10-27T00:00:00Z',source_refs=test.source_refs)
    from app.institutional_newsroom_v1120 import assess as campaign_newsroom
    source_news=campaign_newsroom(NewsroomPreview(newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',entries=[entry]),org)
    announcement=make_node(synthetic=True,organization_id=org,node_ref='node:announcement',kind='announcement',research_ref=test.object_ref,research_revision=test.revision,artifact_ref=entry.announcement_ref,artifact_revision=entry.revision,source_release='11.2.0',source_hash_kind='envelope',source_digest=source_news['sha256'],source_refs=tuple(entry.source_refs),parents=(EvidencePointer(synthetic=True,organization_id=org,node_ref=evidence.node_ref,evidence_sha256=evidence.evidence_sha256),))
    campaign_object=CommunicationObject(synthetic=True,organization_id=org,communication_ref='communication:campaign',revision='r1',root_node_ref=evidence.node_ref,nodes=(evidence,announcement))
    campaign_input=Campaign(synthetic=True,organization_id=org,campaign_ref='campaign:fixture',revision='r1',communication=campaign_object,communication_sha256=preview_object(campaign_object,org)['sha256'],announcement_evidence=EvidencePointer(synthetic=True,organization_id=org,node_ref=announcement.node_ref,evidence_sha256=announcement.evidence_sha256),source_entry=entry,source_distribution=StrictDistribution(**test.model_dump()),newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',channels=('newsroom','digest'),topics=('methods-data',))
    campaign_result=compose_campaign(campaign_input,org)
    data['v1220_unreviewed_bundle_withheld']=campaign_result['variations']==[] and campaign_result['eligible_for_bundle_only'] is False
    data['v1220_no_recipients_or_dispatch']=all(campaign_result[k] is False for k in ('production_certified','production_writes_enabled','recipient_collection_enabled','campaign_dispatch_enabled','recipient_selection_performed','persisted'))
    data['v1220_gates_and_mode']=campaign_result['live_acceptance_gates_pending']==list(pending) and manifest.get('campaign_composer_mode')=='synthetic-source-regenerated-channel-bundles-no-recipients-or-dispatch'
    from app.rights_suppression_v1230 import PurposeRule, RetentionRule, PolicySimulation, simulate_policy
    policy_input=PolicySimulation(synthetic=True,organization_id=org,policy_ref='policy:fixture',revision='r1',campaign=campaign_input,campaign_sha256=campaign_result['sha256'],as_of='2026-10-27T00:00:00Z',purpose_rule=PurposeRule(synthetic=True,organization_id=org,purpose='research-alert'),retention=RetentionRule(synthetic=True,organization_id=org))
    policy_result=simulate_policy(policy_input,org)
    data['v1230_missing_metadata_denied']=policy_result['eligible_variations']==[] and all(not d['eligible_for_synthetic_policy_preview_only'] for d in policy_result['channel_decisions'])
    data['v1230_no_consent_mutation_or_writes']=all(policy_result[k] is False for k in ('production_certified','production_writes_enabled','consent_verified','consent_changed','erasure_authorized','actual_records_deleted','policy_authorizes_delivery','legal_determination','persisted'))
    data['v1230_gates_and_mode']=policy_result['live_acceptance_gates_pending']==list(pending) and manifest.get('communications_policy_mode')=='synthetic-purpose-rights-retention-embargo-deny-default-no-consent-mutation'
    from app.editorial_workflows_v1240 import ReviewWorkflow, simulate_workflow
    workflow_input=ReviewWorkflow(synthetic=True,organization_id=org,workflow_ref='workflow:fixture',revision='r1',author_ref='synthetic:'+str(uuid4()),policy=policy_input,policy_sha256=policy_result['sha256'],as_of=policy_input.as_of)
    workflow_result=simulate_workflow(workflow_input,org)
    data['v1240_missing_roles_deny']=workflow_result['all_reviews_complete_for_simulation'] is False and workflow_result['eligible_variations']==[] and len(workflow_result['reviews'])==4
    data['v1240_no_live_approval_or_writes']=all(workflow_result[k] is False for k in ('production_certified','production_writes_enabled','reviewer_identities_verified','reviewer_roles_verified','live_approval_executed','delivery_authorized','roles_changed','persisted'))
    data['v1240_gates_and_mode']=workflow_result['live_acceptance_gates_pending']==list(pending) and manifest.get('editorial_workflows_mode')=='immutable-synthetic-review-decisions-no-self-approval-or-delivery'
    from app.templates_v1250 import TemplateRequest, render_template, TEMPLATES
    template_result=render_template(TemplateRequest(synthetic=True,organization_id=org,template='newsroom',workflow=workflow_input,workflow_sha256=workflow_result['sha256']),org)
    data['v1250_unreviewed_template_withheld']=template_result['document'] is None and template_result['html_fragment_preview'] is None and len(TEMPLATES)==6
    data['v1250_no_public_renderer_or_delivery']=all(template_result[k] is False for k in ('production_certified','production_writes_enabled','delivery_authorized','channel_distribution_approval_granted','public_renderer_enabled','remote_resources_enabled','wcag_conformance_certified','persisted'))
    data['v1250_gates_and_mode']=template_result['live_acceptance_gates_pending']==list(pending) and manifest.get('institutional_templates_mode')=='private-evidence-bound-structured-templates-no-public-renderer-or-dispatch'
    return data

def http_get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'SCEC-certification/8.9.0'}),timeout=5) as res:
            return res.status,res.read(65536).decode('utf-8','replace')
    except urllib.error.HTTPError as err:
        return err.code,''
    except Exception:
        return None,''

def check_live():
    data={}
    web='http://127.0.0.1:8097'
    backend='http://127.0.0.1:8816'
    status,body=http_get(web+'/healthz')
    data['web_healthz']=status==200 and body.strip()=='ok'
    status,body=http_get(web+'/')
    data['web_serves_870_shell']=status==200 and 'RELEASE 8.7.0' in body
    status,body=http_get(backend+'/health')
    try: obj=json.loads(body)
    except ValueError: obj={}
    data['backend_860_health']=status==200 and obj.get('version')=='8.6.0' and obj.get('status')=='ok'
    status,_=http_get(backend+'/v1/contracts/canonical')
    data['unauthenticated_rejected']=status==401
    data['web_port_bound_loopback']=False
    try:
        result=subprocess.run(['docker','inspect','--format','{{json .NetworkSettings.Ports}}','scec-engagement-web-v870'],capture_output=True,text=True,timeout=5)
        data['web_port_bound_loopback']=result.returncode==0 and '127.0.0.1' in result.stdout and '8097' in result.stdout
    except Exception: pass
    return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Read-only checks against local Contabo ports; no public network exposure')
    parser.add_argument('--json-out',help='Optional report destination')
    args=parser.parse_args()
    source=check_source(); live=check_live() if args.live else {}
    # Public HTTPS, browser acceptance, identity brokering and tenant-scope tests require separate evidence.
    pending=['public_https_dns_tls','wordpress_public_launcher_acceptance','authenticated_human_session','csrf_revocation_session_expiry','live_tenant_isolation_roles','privacy_retention_policy','staged_persistence_write_certification']
    passed=all(source.values()) and (not args.live or all(live.values()))
    report={'release':json.loads((ROOT/'RELEASE-MANIFEST.json').read_text())['version'],'source_checks':source,'live_checks':live,'gates_not_certified':pending,'preflight':'PASS' if passed else 'FAIL','production_certified':False,'production_writes_enabled':False}
    encoded=json.dumps(report,indent=2,sort_keys=True)
    print(encoded)
    if args.json_out: Path(args.json_out).write_text(encoded+'\n')
    return 0 if passed else 1
if __name__=='__main__': sys.exit(main())
