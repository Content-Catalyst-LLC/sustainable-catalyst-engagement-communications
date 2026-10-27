import time
from html.parser import HTMLParser
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.templates_v1250 import TemplateRequest, render_template, TEMPLATES, BLOCKED_ACTIONS
from app.campaigns_v1220 import Campaign, compose_campaign
from app.communication_objects_v1200 import make_node, CommunicationObject, EvidencePointer, preview_object
from app.editorial_workflows_v1240 import simulate_workflow
from app.events_v1160 import Event, Speaker, preview_event
from app.citation_discovery_v1150 import Publication, Author, export
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production';SYNTH={'synthetic':True,'organization_id':ORG}

@pytest.fixture
def template_factory(campaign_factory,policy_factory,workflow_factory):
    def build(template='newsroom',event_changes=None,publication_changes=None,**changes):
        campaign=campaign_factory();additional=None;event=None;publication=None
        root=next(n for n in campaign.communication.nodes if n.kind=='research')
        if template=='webinar-notice':
            event=Event(**{**dict(event_ref='event:fixture',revision=0,kind='webinar',title='Synthetic webinar',description='Synthetic discussion',canonical_url='https://example.org/event',starts_at='2026-11-01T12:00:00Z',ends_at='2026-11-01T13:00:00Z',updated_at='2026-10-27T00:00:00Z',timezone_name='UTC',lifecycle='scheduled',source_refs=['source:fixture'],speakers=[Speaker(speaker_ref='synthetic:'+str(UUID(int=50)),attribution='Synthetic Speaker',privacy_reviewed=True,attribution_reviewed=True,**SYNTH)],editorial_reviewed=True,rights_reviewed=True,privacy_reviewed=True,**SYNTH),**(event_changes or {})})
            kind='event';artifact_ref=event.event_ref;revision='seq:'+str(event.revision);digest=preview_event(event,ORG)['sha256'];release='11.6.0'
        if template=='publication-summary':
            publication=Publication(**{**dict(object_ref='publication:fixture',revision='r1',title='Synthetic publication',authors=[Author(name='Synthetic Author',**SYNTH)],year=2026,canonical_url='https://example.org/publication',source_refs=['source:fixture'],**SYNTH),**(publication_changes or {})})
            kind='citation';artifact_ref=publication.object_ref;revision=publication.revision;digest=export(publication,ORG)['sha256'];release='11.5.0'
        if event is not None or publication is not None:
            node=make_node(node_ref='node:'+kind,kind=kind,research_ref=root.research_ref,research_revision=root.research_revision,artifact_ref=artifact_ref,artifact_revision=revision,source_release=release,source_hash_kind='envelope',source_digest=digest,source_refs=('source:fixture',),parents=(EvidencePointer(node_ref=root.node_ref,evidence_sha256=root.evidence_sha256,**SYNTH),),**SYNTH)
            obj=CommunicationObject(**{**campaign.communication.model_dump(),'nodes':(*campaign.communication.nodes,node)})
            campaign=Campaign(**{**campaign.model_dump(),'communication':obj,'communication_sha256':preview_object(obj,ORG)['sha256']})
            additional=EvidencePointer(node_ref=node.node_ref,evidence_sha256=node.evidence_sha256,**SYNTH)
        policy=policy_factory(campaign=campaign,campaign_sha256=compose_campaign(campaign,ORG)['sha256'])
        workflow=workflow_factory(policy=policy)
        return TemplateRequest(**{**dict(template=template,workflow=workflow,workflow_sha256=simulate_workflow(workflow,ORG)['sha256'],additional_evidence=additional,event=event,publication=publication,**SYNTH),**changes})
    return build

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_TEMPLATES_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-template-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


@pytest.mark.parametrize('kind',TEMPLATES)
def test_six_branded_structured_templates_remain_private(template_factory,kind):
    r=render_template(template_factory(kind),ORG)
    doc=r['document'];assert doc and doc['brand']=='Sustainable Catalyst' and doc['template']==kind
    assert doc['heading']['level']==1 and all(s['level']==2 for s in doc['sections'])
    assert all(link['label'].startswith('Read the ') for link in doc['links'])
    assert doc['images']==[] and doc['source_refs']==['source:fixture'] and doc['language']=='en'
    assert all(r[k] is False for k in DISABLED) and len(r['live_acceptance_gates_pending'])==7
    for flag in ['delivery_authorized','channel_distribution_approval_granted','public_renderer_enabled','remote_resources_enabled','wcag_conformance_certified']:assert r[flag] is False


def test_fixed_markup_has_heading_structure_and_no_active_elements(template_factory):
    r=render_template(template_factory(),ORG)
    class Inspect(HTMLParser):
        def __init__(self):super().__init__();self.tags=[];self.attrs=[]
        def handle_starttag(self,tag,attrs):self.tags.append(tag);self.attrs.extend(attrs)
    p=Inspect();p.feed(r['html_fragment_preview'])
    assert p.tags.count('h1')==1 and p.tags.count('h2')>=1
    assert not {'script','style','iframe','img','form','button','input','object'}.intersection(p.tags)
    assert all(not key.startswith('on') for key,value in p.attrs)
    assert ('lang','en') in p.attrs and ('aria-label','Research source references') in p.attrs
    assert "default-src 'none'" in r['required_future_html_headers']['Content-Security-Policy']


def test_escaped_optional_metadata_and_no_invented_doi(template_factory):
    r=render_template(template_factory('publication-summary',publication_changes={'title':'Synthetic "title" & record'}),ORG)
    assert '&quot;title&quot; &amp; record' in r['html_fragment_preview']
    assert any('No DOI supplied' in s['paragraphs'] for s in r['document']['sections'])
    assert 'Supplied DOI' not in r['html_fragment_preview']


def test_publication_notices_preserved(template_factory):
    from app.citation_discovery_v1150 import Relation
    relation=Relation(kind='retraction',url='https://example.org/retraction',source_ref='source:fixture',**SYNTH)
    r=render_template(template_factory('publication-summary',publication_changes={'relations':[relation]}),ORG)
    assert any(s['heading']=='Retraction notice' for s in r['document']['sections'])
    assert any(link['url']==relation.url for link in r['document']['links'])


def test_missing_optional_facts_or_ineligible_event_withholds(template_factory):
    p=template_factory();p=TemplateRequest(**{**p.model_dump(),'template':'webinar-notice'})
    assert render_template(p,ORG)['document'] is None
    assert 'event-evidence-missing' in render_template(p,ORG)['withheld_reasons']
    r=render_template(template_factory('webinar-notice',event_changes={'privacy_reviewed':False}),ORG)
    assert r['document'] is None and r['html_fragment_preview'] is None
    with pytest.raises(ValidationError):template_factory('webinar-notice',event_changes={'kind':'event'})


def test_review_incomplete_withholds_all_markup(template_factory):
    p=template_factory();wf=p.workflow.model_dump();wf['decisions']=()
    from app.editorial_workflows_v1240 import ReviewWorkflow
    workflow=ReviewWorkflow(**wf)
    p=TemplateRequest(**{**p.model_dump(),'workflow':workflow,'workflow_sha256':simulate_workflow(workflow,ORG)['sha256']})
    r=render_template(p,ORG);assert r['document'] is None and r['html_fragment_preview'] is None
    assert r['withheld_reasons']==['workflow-review-incomplete']


@pytest.mark.parametrize('kind,field,value',[('publication-summary','title','Altered source title'),('publication-summary','year',2025),('webinar-notice','title','Altered event title'),('webinar-notice','starts_at','2026-11-01T12:30:00Z')])
def test_optional_facts_cannot_reuse_reviewed_digest(template_factory,kind,field,value):
    data=template_factory(kind).model_dump();key='event' if kind=='webinar-notice' else 'publication';data[key][field]=value
    with pytest.raises(ValidationError):TemplateRequest(**data)


def test_stale_workflow_pointer_tenant_and_injection(template_factory):
    with pytest.raises(ValidationError):template_factory(workflow_sha256='a'*64)
    with pytest.raises(ValidationError):template_factory(organization_id=OTHER)
    with pytest.raises(ValidationError):template_factory('publication-summary',publication_changes={'title':'<script>bad</script>'})
    with pytest.raises(ValidationError):template_factory(html='<script>bad</script>')
    with pytest.raises(ValueError):render_template(template_factory(),OTHER)
    p=template_factory('publication-summary');data=p.model_dump();data['additional_evidence']['evidence_sha256']='a'*64
    with pytest.raises(ValidationError):TemplateRequest(**data)


def test_http_scope_default_off_and_private_errors(client,template_factory,monkeypatch):
    url='/v1/institutional-templates/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=template_factory().model_dump(mode='json');success=client.post('/v1/institutional-templates/preview',headers=headers(),json=data)
    assert success.status_code==200 and success.headers['content-type'].startswith('application/json')
    assert success.headers['Cache-Control']=='no-store, private' and success.headers['X-Frame-Options']=='DENY'
    data['email']='private@example.org';r=client.post('/v1/institutional-templates/preview',headers=headers(),json=data);assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_TEMPLATES_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_live_templates_or_delivery(client,action):
    assert client.post('/v1/institutional-templates/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/institutional-templates/status',headers=headers()).status_code==503
