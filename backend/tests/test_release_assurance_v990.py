import os,time
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.release_assurance_v990 import evaluate,digest,GATES,Evidence
client=TestClient(app)
def auth(monkeypatch,role='administrator'):
    org=uuid4();secret='release-assurance-test-key-0123456789abcdef'
    monkeypatch.setenv('SCEC_ASSURANCE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='reviewer',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return org,{'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}
def test_disabled(monkeypatch):
    monkeypatch.delenv('SCEC_ASSURANCE_STAGING_ENABLED',raising=False)
    assert client.get('/v1/release-assurance/status').status_code in (401,503)
def test_unauthed(monkeypatch):
    monkeypatch.setenv('SCEC_ASSURANCE_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.get('/v1/release-assurance/status').status_code==401
def test_status(monkeypatch):
    _,headers=auth(monkeypatch)
    r=client.get('/v1/release-assurance/status',headers=headers)
    assert r.status_code==200,r.text
    assert r.json()['production_certified'] is False
    assert r.json()['mutation_permitted'] is False
def test_preview_never_certifies(monkeypatch):
    _,headers=auth(monkeypatch)
    r=client.post('/v1/release-assurance/assessment-preview',headers=headers,json={'evidence':[{'gate':g,'verified':True,'evidence_reference':'mock:1'} for g in GATES]})
    assert r.status_code==200,r.text
    report=r.json()['report']
    assert report['production_certified'] is False and report['promotion_permitted'] is False
    assert all(not e['independently_verified'] for e in report['evidence'])
    assert r.json()['report_sha256']==digest(report)
def test_preview_empty(monkeypatch):
    _,h=auth(monkeypatch)
    r=client.post('/v1/release-assurance/assessment-preview',headers=h,json={})
    assert r.status_code==200
    assert len(r.json()['report']['gates_not_independently_certified'])==7
def test_flag_detect(monkeypatch):
    _,h=auth(monkeypatch);monkeypatch.setenv('SCEC_OUTBOUND_ENABLED','1')
    r=client.post('/v1/release-assurance/assessment-preview',headers=h,json={})
    assert 'SCEC_OUTBOUND_ENABLED' in r.json()['report']['enabled_forbidden_flags']
def test_no_role(monkeypatch):
    _,h=auth(monkeypatch,'viewer')
    assert client.get('/v1/release-assurance/status',headers=h).status_code==403
def test_cross_tenant(monkeypatch):
    _,h=auth(monkeypatch);h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.get('/v1/release-assurance/status',headers=h).status_code in (401,403)
def test_allowlist(monkeypatch):
    _,h=auth(monkeypatch);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/release-assurance/status',headers=h).status_code==403
def test_reliability_does_not_probe(monkeypatch):
    _,h=auth(monkeypatch);r=client.get('/v1/release-assurance/reliability-preview',headers=h)
    assert r.status_code==200
    assert r.json()['report']['db']=='not-probed'
def test_mutations_blocked_with_flags_set(monkeypatch):
    _,h=auth(monkeypatch)
    for flag in ('SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):monkeypatch.setenv(flag,'1')
    for action in ('promote','commit','enable-writes','enable-outbound','enable-deletion','enable-federation'):
        r=client.post('/v1/release-assurance/'+action,headers=h)
        assert r.status_code==503,(action,r.text)
def test_extra_field_rejected(monkeypatch):
    _,h=auth(monkeypatch)
    assert client.post('/v1/release-assurance/assessment-preview',headers=h,json={'secret':'x'}).status_code==422
def test_duplicate_evidence(monkeypatch):
    _,h=auth(monkeypatch)
    r=client.post('/v1/release-assurance/assessment-preview',headers=h,json={'evidence':[{'gate':GATES[0]},{'gate':GATES[0]}]})
    assert r.status_code==422
def test_unknown_evidence(monkeypatch):
    _,h=auth(monkeypatch)
    assert client.post('/v1/release-assurance/assessment-preview',headers=h,json={'evidence':[{'gate':'not-a-gate'}]}).status_code==422
def test_digest_order():
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})
