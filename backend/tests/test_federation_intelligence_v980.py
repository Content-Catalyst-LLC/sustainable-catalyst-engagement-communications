import time
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.federation_intelligence_v980 import ApplicationHandoff,evaluate,fingerprint
client=TestClient(app)

def authorized(monkeypatch,role='administrator'):
    org=uuid4();secret='federation-test-key-01234567890123456789'
    monkeypatch.setenv('SCEC_FEDERATION_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='test-reviewer',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return org,{'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}

def sample(org,**kw):
    return {'source_app':'workspace','destination_app':'library','requested_capability':'view-tenant-summary',
            'subject_reference':'opaque:sample-123','tenant_reference':str(org)}|kw

def test_disabled(monkeypatch):
    monkeypatch.delenv('SCEC_FEDERATION_STAGING_ENABLED',raising=False)
    assert client.get('/v1/federation-intelligence/status').status_code in (401,503)

def test_anonymous(monkeypatch):
    monkeypatch.setenv('SCEC_FEDERATION_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.get('/v1/federation-intelligence/status').status_code==401

def test_status(monkeypatch):
    _,h=authorized(monkeypatch)
    r=client.get('/v1/federation-intelligence/status',headers=h)
    assert r.status_code==200,r.text
    assert r.json()['federation_enabled'] is False

def test_preview(monkeypatch):
    org,h=authorized(monkeypatch)
    r=client.post('/v1/federation-intelligence/handoff-preview',headers=h,json=sample(org))
    assert r.status_code==200,r.text
    report=r.json()['report']
    assert report['federation_authorized'] is False and report['token_exchanged'] is False
    assert report['data_transferred'] is False and report['persisted'] is False
    assert r.json()['deterministic_sha256']==fingerprint(report)

def test_compatibility(monkeypatch):
    org,h=authorized(monkeypatch)
    r=client.post('/v1/federation-intelligence/compatibility-preview',headers=h,json={'requests':[sample(org),sample(org,source_app='workbench')]})
    assert r.status_code==200,r.text
    assert r.json()['report']['count']==2
    assert r.json()['report']['data_transferred'] is False

def test_cross_tenant_rejected(monkeypatch):
    _,h=authorized(monkeypatch)
    r=client.post('/v1/federation-intelligence/handoff-preview',headers=h,json=sample(uuid4()))
    assert r.status_code==403

def test_cross_tenant_batch_rejected(monkeypatch):
    org,h=authorized(monkeypatch)
    r=client.post('/v1/federation-intelligence/compatibility-preview',headers=h,json={'requests':[sample(org),sample(uuid4())]})
    assert r.status_code==403

def test_allowlist(monkeypatch):
    _,h=authorized(monkeypatch)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/federation-intelligence/status',headers=h).status_code==403

def test_role_denied(monkeypatch):
    _,h=authorized(monkeypatch,'viewer')
    assert client.get('/v1/federation-intelligence/status',headers=h).status_code==403

def test_gates_even_when_enabled(monkeypatch):
    _,h=authorized(monkeypatch)
    for name in ('SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):
        monkeypatch.setenv(name,'1')
    for path in ('token-exchange','link-identity','handoff-commit','commit'):
        r=client.post('/v1/federation-intelligence/'+path,headers=h)
        assert r.status_code==503,(path,r.text)

def test_extra_pii_rejected(monkeypatch):
    org,h=authorized(monkeypatch)
    assert client.post('/v1/federation-intelligence/handoff-preview',headers=h,json=sample(org,email='person@example.org')).status_code==422

def test_unsupported_app_rejected(monkeypatch):
    org,h=authorized(monkeypatch)
    assert client.post('/v1/federation-intelligence/handoff-preview',headers=h,json=sample(org,destination_app='unknown')).status_code==422

def test_batch_limit(monkeypatch):
    org,h=authorized(monkeypatch)
    assert client.post('/v1/federation-intelligence/compatibility-preview',headers=h,json={'requests':[sample(org)]*26}).status_code==422

def test_no_identity_mode(monkeypatch):
    _,h=authorized(monkeypatch)
    monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/federation-intelligence/status',headers=h).status_code in (401,503)

def test_digest_deterministic():
    value={'a':1,'b':2};assert fingerprint(value)==fingerprint({'b':2,'a':1})
