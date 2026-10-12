import os,time
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.unified_v1000 import snapshot,digest,DOMAINS,PAGES
client=TestClient(app)
def auth(monkeypatch,role='administrator'):
    org=uuid4();secret='unified-release-test-key-0123456789abcdef'
    monkeypatch.setenv('SCEC_UNIFIED_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='reviewer',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return org,{'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}
def test_default_closed(monkeypatch):
    monkeypatch.delenv('SCEC_UNIFIED_STAGING_ENABLED',raising=False)
    assert client.get('/v1/unified-platform/status').status_code in (401,503)
def test_no_auth(monkeypatch):
    monkeypatch.setenv('SCEC_UNIFIED_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.get('/v1/unified-platform/status').status_code==401
def test_status(monkeypatch):
    _,h=auth(monkeypatch);r=client.get('/v1/unified-platform/status',headers=h)
    assert r.status_code==200 and r.json()['version']=='10.0.0' and not r.json()['writes_enabled']
def test_catalog(monkeypatch):
    _,h=auth(monkeypatch);r=client.get('/v1/unified-platform/catalog',headers=h)
    assert r.status_code==200 and len(r.json()['domains'])==10
    assert r.json()['wordpress_pages']==list(PAGES)
def test_readiness(monkeypatch):
    _,h=auth(monkeypatch);r=client.get('/v1/unified-platform/readiness',headers=h)
    assert r.status_code==200 and r.json()['sha256']==digest(r.json()['report'])
    assert len(r.json()['report']['pending_production_gates'])==7
def test_preview(monkeypatch):
    _,h=auth(monkeypatch);r=client.post('/v1/unified-platform/consolidation-preview',headers=h,json={'domains':['engagement-analytics']})
    assert r.status_code==200 and not r.json()['persisted'] and r.json()['report']['human_approval_required']
def test_invalid_domain(monkeypatch):
    _,h=auth(monkeypatch)
    for domains in [['unknown'],['human-auth','human-auth']]:
        assert client.post('/v1/unified-platform/consolidation-preview',headers=h,json={'domains':domains}).status_code==422
def test_no_role(monkeypatch):
    _,h=auth(monkeypatch,'viewer');assert client.get('/v1/unified-platform/status',headers=h).status_code==403
def test_cross_tenant(monkeypatch):
    _,h=auth(monkeypatch);h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.get('/v1/unified-platform/status',headers=h).status_code in (401,403)
def test_allowlist(monkeypatch):
    _,h=auth(monkeypatch);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/unified-platform/status',headers=h).status_code==403
def test_denied_actions_even_with_flags(monkeypatch):
    _,h=auth(monkeypatch)
    for flag in ('SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):monkeypatch.setenv(flag,'1')
    for action in ('commit','promote','enable-live'):
        assert client.post('/v1/unified-platform/'+action,headers=h).status_code==503
    assert len(client.get('/v1/unified-platform/readiness',headers=h).json()['report']['enabled_forbidden_flags'])==4
def test_snapshot_never_certifies():
    assert snapshot()['production_certified'] is False
    assert snapshot()['live_data_loaded'] is False
    assert digest({'a':1,'b':2})==digest({'b':2,'a':1})
