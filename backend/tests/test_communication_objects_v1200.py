import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.communication_objects_v1200 import EvidenceFacts, EvidenceNode, EvidencePointer, CommunicationObject, make_node, preview_object, RELEASES, HASH_KINDS, BLOCKED_ACTIONS
from app.research_distribution_v1100 import DistributionPreview, preview
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production'
SYNTH={'synthetic':True,'organization_id':ORG}

def node(kind='research',**changes):
    data=dict(node_ref='node:'+kind,kind=kind,research_ref='research:fixture',research_revision='r1',artifact_ref='research:fixture' if kind=='research' else 'artifact:'+kind,artifact_revision='r1',source_release=RELEASES[kind],source_hash_kind=HASH_KINDS[kind],source_digest=hashlib.sha256(('synthetic-source-'+kind).encode()).hexdigest(),source_refs=('source:fixture',),**SYNTH)
    if kind!='research':
        root=node();data['parents']=(EvidencePointer(node_ref=root.node_ref,evidence_sha256=root.evidence_sha256,**SYNTH),)
    data.update(changes);return make_node(**data)

def obj(**changes):
    return CommunicationObject(**{**dict(communication_ref='communication:fixture',revision='r1',root_node_ref='node:research',nodes=(node(),node('feed')),**SYNTH),**changes})

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_OBJECTS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-object-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_all_typed_v11_artifacts_have_hash_checked_lineage():
    p=obj(nodes=tuple(node(k) for k in RELEASES));r=preview_object(p,ORG)
    assert len(r['object']['nodes'])==10 and r['schema_version']=='scec.communication-object/1'
    assert all(r[k] is False for k in DISABLED) and len(r['live_acceptance_gates_pending'])==7
    assert r['source_digests_independently_verified'] is False
    assert r==preview_object(obj(nodes=tuple(reversed(p.nodes))),ORG)


def test_actual_v11_distribution_digest_is_preserved():
    legacy=preview(DistributionPreview(object_ref='research:fixture',revision='r1',object_kind='publication',targets=['rss'],source_refs=['source:fixture']),ORG)
    root=node(source_digest=legacy['manifest_sha256'])
    result=preview_object(obj(nodes=(root,)),ORG)
    assert result['object']['nodes'][0]['source_digest']==legacy['manifest_sha256']
    assert result['object']['nodes'][0]['source_hash_kind']=='source-manifest'
    assert not legacy['publication_authorized'] and result['production_certified'] is False


def test_node_digest_detects_tampering_and_contracts_are_frozen():
    root=node();data=root.model_dump();data['source_digest']='a'*64
    with pytest.raises(ValidationError):EvidenceNode(**data)
    with pytest.raises(ValidationError):root.artifact_revision='r2'
    with pytest.raises(ValidationError):obj().nodes=()
    assert isinstance(root.source_refs,tuple) and isinstance(node('feed').parents,tuple)


@pytest.mark.parametrize('kind',list(RELEASES)[1:])
def test_orphan_kind_requires_parent(kind):
    with pytest.raises(ValidationError):node(kind,parents=())


def test_unknown_parent_and_stale_parent_are_rejected():
    root=node()
    orphan=node('feed',parents=(EvidencePointer(node_ref='node:missing',evidence_sha256=root.evidence_sha256,**SYNTH),))
    with pytest.raises(ValidationError):obj(nodes=(root,orphan))
    with pytest.raises(ValidationError):obj(nodes=(node(source_digest='b'*64),node('feed')))


def test_cycle_traversal_independently_rejects_closed_component():
    # Deliberately bypass node validation only to unit-test graph traversal;
    # equivalent wire input is already rejected by digest validation.
    root=node();a=node('feed');b=node('alert')
    a=EvidenceNode.model_construct(**{**a.model_dump(), 'parents':(EvidencePointer(node_ref=b.node_ref,evidence_sha256=b.evidence_sha256,**SYNTH),)})
    b=EvidenceNode.model_construct(**{**b.model_dump(), 'parents':(EvidencePointer(node_ref=a.node_ref,evidence_sha256=a.evidence_sha256,**SYNTH),)})
    unchecked=CommunicationObject.model_construct(**{**obj().model_dump(),'nodes':(root,a,b)})
    with pytest.raises(ValueError,match='Cyclic'):unchecked.graph()


@pytest.mark.parametrize('changes',[{'research_revision':'r2'},{'research_ref':'research:other'},{'source_refs':('source:other',)}])
def test_cross_research_or_unregistered_sources(changes):
    with pytest.raises(ValidationError):obj(nodes=(node(),node('feed',**changes)))


def test_tenant_duplicate_and_source_semantics():
    with pytest.raises(ValidationError):obj(nodes=(node(organization_id=OTHER),))
    with pytest.raises(ValidationError):obj(nodes=(node(),node()))
    with pytest.raises(ValidationError):obj(root_node_ref='node:missing')
    with pytest.raises(ValidationError):node('feed',source_release='11.3.0')
    with pytest.raises(ValidationError):node('feed',source_hash_kind='envelope')
    with pytest.raises(ValidationError):node('feed',artifact_revision=0)
    with pytest.raises(ValidationError):node('feed',email='private@example.org')
    with pytest.raises(ValueError):preview_object(obj(),OTHER)


def test_revision_changes_invalidate_digest_links():
    old=obj();root=node(research_revision='r2',artifact_revision='r2')
    pointer=EvidencePointer(node_ref=root.node_ref,evidence_sha256=root.evidence_sha256,**SYNTH)
    new=obj(revision='r2',nodes=(root,node('feed',research_revision='r2',parents=(pointer,))))
    assert preview_object(old,ORG)['sha256']!=preview_object(new,ORG)['sha256']


def test_http_scope_and_validation_redaction(client,monkeypatch):
    url='/v1/communication-objects/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=obj().model_dump(mode='json');assert client.post('/v1/communication-objects/preview',headers=headers(),json=data).status_code==200
    data['nodes'][0]['email']='private@example.org';r=client.post('/v1/communication-objects/preview',headers=headers(),json=data)
    assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_OBJECTS_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_live_object_operations(client,action):
    assert client.post('/v1/communication-objects/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/communication-objects/status',headers=headers()).status_code==503
