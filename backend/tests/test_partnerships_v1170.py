import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.partnerships_v1170 import Partner, Artifact, PartnerPackage, plan, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production'

def partner(**changes):
    return Partner(**{**dict(synthetic=True,organization_id=ORG,partner_ref='partner:fixture',institution_ref='institution:other',kind='academic',accepted_licenses=['cc-by'],allowed_classifications=['public'],institutional_reviewed=True,rights_reviewed=True),**changes})

def artifact(**changes):
    return Artifact(**{**dict(synthetic=True,organization_id=ORG,object_ref='object:fixture',revision='r1',object_kind='publication',source_refs=['source:fixture'],license='cc-by',classification='public',rights_reviewed=True,editorial_reviewed=True,privacy_reviewed=True,source_integrity_reviewed=True,distribution_reviewed=True),**changes})

def package(**changes):
    return PartnerPackage(**{**dict(synthetic=True,organization_id=ORG,package_ref='package:fixture',revision='r1',institution_ref='institution:owner',artifacts=[artifact()],partners=[partner()]),**changes})

def decision(**changes):return plan(package(**changes),ORG)['routing_decisions'][0]

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_PARTNERS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-partner-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_eligible_plan_still_cannot_export():
    r=plan(package(),ORG)
    assert r['routing_decisions'][0]['eligible_for_synthetic_plan_only'] is True
    assert all(r[k] is False for k in DISABLED)
    assert not r['data_exported'] and not r['federation_authorized'] and not r['partner_delivery_enabled']
    source=r['distribution_manifests'][0]['source_manifest']
    assert source['release']=='11.0.0' and source['human_review_complete'] is True
    assert source['publication_authorized'] is False and source['organization_id']==ORG
    assert len(r['live_acceptance_gates_pending'])==7


@pytest.mark.parametrize('gate',['rights_reviewed','editorial_reviewed','privacy_reviewed','source_integrity_reviewed','distribution_reviewed'])
def test_artifact_review_gate(gate):
    d=decision(artifacts=[artifact(**{gate:False})]);assert not d['eligible_for_synthetic_plan_only'] and 'artifact-review-required' in d['review_flags']
    with pytest.raises(ValidationError):artifact(**{gate:'yes'})


@pytest.mark.parametrize('changes,reason',[({'institutional_reviewed':False},'institutional-review-required'),({'rights_reviewed':False},'partner-rights-review-required'),({'suppressed':True},'partner-suppressed'),({'accepted_licenses':['cc-by-sa']},'license-not-accepted'),({'allowed_classifications':['internal']},'access-classification-denied')])
def test_partner_policy_denials(changes,reason):
    d=decision(partners=[partner(**changes)]);assert reason in d['review_flags'] and not d['eligible_for_synthetic_plan_only']


def test_institution_boundary_and_restricted_data():
    a=artifact(classification='internal');p=partner(allowed_classifications=['internal'])
    assert 'institution-boundary-denied' in decision(artifacts=[a],partners=[p])['review_flags']
    p=partner(institution_ref='institution:owner',allowed_classifications=['internal'])
    assert decision(artifacts=[a],partners=[p])['eligible_for_synthetic_plan_only']
    assert 'restricted-artifact-no-routing' in decision(artifacts=[artifact(classification='restricted')],partners=[partner(institution_ref='institution:owner',allowed_classifications=['restricted'])])['review_flags']
    assert 'restricted-artifact-no-routing' in decision(artifacts=[artifact(license='restricted')],partners=[partner(accepted_licenses=['restricted'])])['review_flags']
    assert 'license-unknown' in decision(artifacts=[artifact(license='unknown')],partners=[partner(accepted_licenses=['unknown'])])['review_flags']


def test_one_denied_object_blocks_whole_package():
    d=decision(artifacts=[artifact(),artifact(object_ref='object:restricted',classification='restricted')])
    assert not d['eligible_for_synthetic_plan_only']


def test_tenant_duplicates_and_actual_contact_fields():
    with pytest.raises(ValidationError):package(partners=[partner(organization_id=OTHER)])
    with pytest.raises(ValidationError):package(artifacts=[artifact(organization_id=OTHER)])
    with pytest.raises(ValidationError):package(partners=[partner(),partner()])
    with pytest.raises(ValidationError):package(artifacts=[artifact(),artifact()])
    with pytest.raises(ValidationError):partner(email='private@example.org')
    with pytest.raises(ValidationError):partner(accepted_licenses=['cc-by','cc-by'])
    with pytest.raises(ValueError):plan(package(),OTHER)


def test_normalized_order_and_revision_evidence():
    p=package(artifacts=[artifact(object_ref='object:b'),artifact(object_ref='object:a')],partners=[partner(partner_ref='partner:b'),partner(partner_ref='partner:a')])
    data=p.model_dump();data['artifacts'].reverse();data['partners'].reverse()
    assert plan(p,ORG)==plan(PartnerPackage(**data),ORG)
    data['revision']='r2';assert plan(p,ORG)['sha256']!=plan(PartnerPackage(**data),ORG)['sha256']


def test_http_bound_identity_and_fail_closed(client,monkeypatch):
    url='/v1/partnerships/status'
    assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=package().model_dump(mode='json');assert client.post('/v1/partnerships/preview',headers=headers(),json=data).status_code==200
    data['partners'][0]['email']='private@example.org'
    r=client.post('/v1/partnerships/preview',headers=headers(),json=data);assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_PARTNERS_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_partner_live_operations(client,action):
    assert client.post('/v1/partnerships/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/partnerships/status',headers=headers()).status_code==503
