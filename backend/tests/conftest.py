"""Shared synthetic operations fixture; no credentials, recipients or transport."""
import time
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.campaigns_v1220 import StrictEntry, StrictDistribution, Campaign, compose_campaign, BLOCKED_ACTIONS
from app.communication_objects_v1200 import make_node, CommunicationObject, EvidencePointer, preview_object
from app.institutional_newsroom_v1120 import NewsroomPreview, assess
from app.research_distribution_v1100 import preview
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production';SYNTH={'synthetic':True,'organization_id':ORG}

def _campaign_fixture(entry_changes=None,distribution_changes=None,**changes):
    entry=StrictEntry(**{**dict(announcement_ref='research:fixture',revision='r1',kind='research-release',editorial_state='approved-preview',headline='Synthetic research headline',summary='Synthetic research summary',canonical_url='https://example.org/research',updated_at='2026-10-27T00:00:00Z',source_refs=['source:fixture'],rights_reviewed=True,editorial_reviewed=True,source_integrity_reviewed=True,privacy_reviewed=True,institutional_approved=True),**(entry_changes or {})})
    dist=StrictDistribution(**{**dict(object_ref=entry.announcement_ref,revision=entry.revision,object_kind='publication',targets=['institutional-newsroom'],source_refs=entry.source_refs,rights_basis='open-license',editorial_reviewed=True,privacy_reviewed=True,source_integrity_reviewed=True,distribution_approved=True),**(distribution_changes or {})})
    news=assess(NewsroomPreview(newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',entries=[entry]),ORG)
    root=make_node(node_ref='node:research',kind='research',research_ref=dist.object_ref,research_revision=dist.revision,artifact_ref=dist.object_ref,artifact_revision=dist.revision,source_release='11.0.0',source_hash_kind='source-manifest',source_digest=preview(dist,ORG)['manifest_sha256'],source_refs=tuple(dist.source_refs),**SYNTH)
    ptr=EvidencePointer(node_ref=root.node_ref,evidence_sha256=root.evidence_sha256,**SYNTH)
    announcement=make_node(node_ref='node:announcement',kind='announcement',research_ref=root.research_ref,research_revision=root.research_revision,artifact_ref=entry.announcement_ref,artifact_revision=entry.revision,source_release='11.2.0',source_hash_kind='envelope',source_digest=news['sha256'],source_refs=tuple(entry.source_refs),parents=(ptr,),**SYNTH)
    obj=CommunicationObject(communication_ref='communication:fixture',revision='r1',root_node_ref=root.node_ref,nodes=(root,announcement),**SYNTH)
    return Campaign(**{**dict(campaign_ref='campaign:fixture',revision='r1',communication=obj,communication_sha256=preview_object(obj,ORG)['sha256'],announcement_evidence=EvidencePointer(node_ref=announcement.node_ref,evidence_sha256=announcement.evidence_sha256,**SYNTH),source_entry=entry,source_distribution=dist,newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',channels=('newsroom','digest','research-alert','press-brief'),topics=('methods-data',),**SYNTH),**changes})


@pytest.fixture
def campaign_factory():
    return _campaign_fixture


@pytest.fixture
def policy_factory(campaign_factory):
    from app.campaigns_v1220 import compose_campaign
    from app.rights_suppression_v1230 import PurposeRule, RightsRule, RetentionRule, PolicySimulation
    def build(**changes):
        campaign=campaign_factory(channels=('digest','research-alert'))
        purpose=PurposeRule(purpose='research-alert',consent_state='granted',consent_reviewed=True,evidence_ref='consent:fixture',allowed_channels=('digest','research-alert'),valid_from='2026-10-26T00:00:00Z',valid_until='2026-10-28T00:00:00Z',**SYNTH)
        rights=RightsRule(source_ref='source:fixture',policy_revision='r1',license='cc-by',rights_reviewed=True,attribution_reviewed=True,**SYNTH)
        retention=RetentionRule(recorded_day='2026-10-01',retention_days=90,privacy_reviewed=True,**SYNTH)
        return PolicySimulation(**{**dict(policy_ref='policy:fixture',revision='r1',campaign=campaign,campaign_sha256=compose_campaign(campaign,ORG)['sha256'],as_of='2026-10-27T00:00:00Z',purpose_rule=purpose,rights=(rights,),retention=retention,classification='public',embargo_reviewed=True,**SYNTH),**changes})
    return build
