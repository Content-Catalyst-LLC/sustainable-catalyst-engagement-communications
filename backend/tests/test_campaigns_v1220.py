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

def campaign(entry_changes=None,distribution_changes=None,**changes):
    entry=StrictEntry(**{**dict(announcement_ref='research:fixture',revision='r1',kind='research-release',editorial_state='approved-preview',headline='Synthetic research headline',summary='Synthetic research summary',canonical_url='https://example.org/research',updated_at='2026-10-27T00:00:00Z',source_refs=['source:fixture'],rights_reviewed=True,editorial_reviewed=True,source_integrity_reviewed=True,privacy_reviewed=True,institutional_approved=True),**(entry_changes or {})})
    dist=StrictDistribution(**{**dict(object_ref=entry.announcement_ref,revision=entry.revision,object_kind='publication',targets=['institutional-newsroom'],source_refs=entry.source_refs,rights_basis='open-license',editorial_reviewed=True,privacy_reviewed=True,source_integrity_reviewed=True,distribution_approved=True),**(distribution_changes or {})})
    news=assess(NewsroomPreview(newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',entries=[entry]),ORG)
    root=make_node(node_ref='node:research',kind='research',research_ref=dist.object_ref,research_revision=dist.revision,artifact_ref=dist.object_ref,artifact_revision=dist.revision,source_release='11.0.0',source_hash_kind='source-manifest',source_digest=preview(dist,ORG)['manifest_sha256'],source_refs=tuple(dist.source_refs),**SYNTH)
    ptr=EvidencePointer(node_ref=root.node_ref,evidence_sha256=root.evidence_sha256,**SYNTH)
    announcement=make_node(node_ref='node:announcement',kind='announcement',research_ref=root.research_ref,research_revision=root.research_revision,artifact_ref=entry.announcement_ref,artifact_revision=entry.revision,source_release='11.2.0',source_hash_kind='envelope',source_digest=news['sha256'],source_refs=tuple(entry.source_refs),parents=(ptr,),**SYNTH)
    obj=CommunicationObject(communication_ref='communication:fixture',revision='r1',root_node_ref=root.node_ref,nodes=(root,announcement),**SYNTH)
    return Campaign(**{**dict(campaign_ref='campaign:fixture',revision='r1',communication=obj,communication_sha256=preview_object(obj,ORG)['sha256'],announcement_evidence=EvidencePointer(node_ref=announcement.node_ref,evidence_sha256=announcement.evidence_sha256,**SYNTH),source_entry=entry,source_distribution=dist,newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',channels=('newsroom','digest','research-alert','press-brief'),topics=('methods-data',),**SYNTH),**changes})

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_CAMPAIGNS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-campaign-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_variations_derive_from_verified_fixture_facts_without_recipients():
    p=campaign();r=compose_campaign(p,ORG)
    assert r['eligible_for_bundle_only'] and len(r['variations'])==4
    assert all(r[k] is False for k in DISABLED)
    for flag in ['recipient_selection_performed','recipient_collection_enabled','campaign_dispatch_enabled']:assert r[flag] is False
    assert len(r['live_acceptance_gates_pending'])==7
    for v in r['variations']:
        assert v['research_ref']==p.source_entry.announcement_ref and v['research_revision']==p.source_entry.revision and v['source_refs']==p.source_entry.source_refs
        assert p.source_entry.headline in str(v['body']) and p.source_entry.summary in str(v['body'])
    digest=next(v for v in r['variations'] if v['channel']=='digest')
    assert json.loads(digest['body']['content_preview'])['items'][0]['title']==p.source_entry.headline
    assert 'recipients' not in str(r)


@pytest.mark.parametrize('gate',['rights_reviewed','editorial_reviewed','source_integrity_reviewed','privacy_reviewed','institutional_approved'])
def test_every_announcement_review_denies_bundle(gate):
    r=compose_campaign(campaign(entry_changes={gate:False}),ORG);assert not r['eligible_for_bundle_only'] and r['variations']==[]
    with pytest.raises(ValidationError):campaign(entry_changes={gate:'yes'})


@pytest.mark.parametrize('gate',['editorial_reviewed','privacy_reviewed','source_integrity_reviewed','distribution_approved'])
def test_distribution_reviews_deny_and_are_hash_bound(gate):
    p=campaign(distribution_changes={gate:False});r=compose_campaign(p,ORG)
    assert not r['eligible_for_bundle_only'] and not r['variations']
    assert r['sha256']!=compose_campaign(campaign(),ORG)['sha256']
    with pytest.raises(ValidationError):campaign(distribution_changes={gate:1})


@pytest.mark.parametrize('state',['draft','editorial-review','archived-preview'])
def test_not_approved_state_has_no_bundle(state):
    assert not compose_campaign(campaign(entry_changes={'editorial_state':state}),ORG)['variations']


def test_suppression_and_unknown_rights():
    assert not compose_campaign(campaign(suppressed=True),ORG)['variations']
    assert not compose_campaign(campaign(distribution_changes={'rights_basis':'not-reviewed'}),ORG)['variations']


@pytest.mark.parametrize('change',[{'headline':'Altered synthetic headline'},{'summary':'Altered synthetic summary'},{'revision':'r2'},{'source_refs':['source:other']}])
def test_tampered_source_cannot_reuse_prior_lineage(change):
    data=campaign().model_dump();data['source_entry'].update(change)
    with pytest.raises(ValidationError):Campaign(**data)


def test_wrong_stale_or_cross_tenant_lineage():
    p=campaign()
    with pytest.raises(ValidationError):campaign(communication_sha256='a'*64)
    with pytest.raises(ValidationError):campaign(announcement_evidence=EvidencePointer(node_ref='node:research',evidence_sha256=p.communication.nodes[0].evidence_sha256,**SYNTH))
    with pytest.raises(ValidationError):campaign(organization_id=OTHER)
    with pytest.raises(ValueError):compose_campaign(p,OTHER)


@pytest.mark.parametrize('changes',[{'channels':('newsroom','newsroom')},{'channels':('email-live',)},{'topics':()},{'recipient_list':['private@example.org']}])
def test_no_arbitrary_channels_or_contact_fields(changes):
    with pytest.raises(ValidationError):campaign(**changes)


def test_content_injection_and_shared_channel_limits():
    for change in [{'headline':'<script>bad</script>'},{'summary':'private@example.org'},{'summary':'s'*501},{'canonical_url':'https://user:secret@example.org/private'}]:
        with pytest.raises(ValidationError):campaign(entry_changes=change)
    assert len(compose_campaign(campaign(entry_changes={'summary':'s'*500}),ORG)['variations'])==4


def test_permutation_and_revision_hashes():
    p=campaign();q=p.model_dump();q['channels']=list(reversed(q['channels']));q['communication']['nodes']=tuple(reversed(q['communication']['nodes']))
    assert compose_campaign(p,ORG)==compose_campaign(Campaign(**q),ORG)
    assert compose_campaign(p,ORG)['sha256']!=compose_campaign(campaign(revision='r2'),ORG)['sha256']


def test_http_scope_default_off_and_private_validation(client,monkeypatch):
    url='/v1/campaign-composer/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=campaign().model_dump(mode='json');assert client.post('/v1/campaign-composer/preview',headers=headers(),json=data).status_code==200
    data['email']='private@example.org';r=client.post('/v1/campaign-composer/preview',headers=headers(),json=data);assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_CAMPAIGNS_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_actual_campaign_operations(client,action):
    assert client.post('/v1/campaign-composer/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/campaign-composer/status',headers=headers()).status_code==503


def test_research_kind_cannot_be_misrepresented():
    with pytest.raises(ValidationError):campaign(entry_changes={'kind':'data-release'})
    assert compose_campaign(campaign(entry_changes={'kind':'data-release'},distribution_changes={'object_kind':'dataset'}),ORG)['eligible_for_bundle_only']
    with pytest.raises(ValidationError):campaign(entry_changes={'kind':'event-notice'})
