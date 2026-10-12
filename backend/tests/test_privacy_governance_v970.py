from datetime import date
from uuid import uuid4
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.privacy_governance_v970 import GovernanceItem,Batch,compute,digest
client=TestClient(app)

def headers(monkeypatch,role='administrator'):
    org=uuid4();secret='privacy-test-signing-secret-0123456789'
    monkeypatch.setenv('SCEC_PRIVACY_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='fixture',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}

def sample(**kw):
    return {'channel':'support','purpose':'support-resolution','legal_basis':'consent','consent_state':'withdrawn','retention_days':30,'collected_day':'2026-01-01'}|kw

def test_disabled(monkeypatch):
    monkeypatch.delenv('SCEC_PRIVACY_STAGING_ENABLED',raising=False)
    assert client.get('/v1/privacy-governance/status').status_code in (401,503)

def test_anonymous_denied(monkeypatch):
    monkeypatch.setenv('SCEC_PRIVACY_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.get('/v1/privacy-governance/status').status_code==401

def test_bound_required(monkeypatch):
    monkeypatch.setenv('SCEC_PRIVACY_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/privacy-governance/status').status_code==503

def test_status(monkeypatch):
    response=client.get('/v1/privacy-governance/status',headers=headers(monkeypatch))
    assert response.status_code==200,response.text
    assert response.json()['deletion_enabled'] is False

def test_preview(monkeypatch):
    r=client.post('/v1/privacy-governance/policy-preview',headers=headers(monkeypatch),json={'records':[sample()],'evaluation_day':'2026-10-12'})
    assert r.status_code==200,r.text
    report=r.json()['report'];assert report['review_flag_counts']['consent-not-established']==1
    assert report['review_flag_counts']['retention-review-due']==1
    assert report['deleted'] is False and report['persisted'] is False
    assert r.json()['deterministic_sha256']==digest(report)

def test_rights_request(monkeypatch):
    r=client.post('/v1/privacy-governance/rights-request-preview',headers=headers(monkeypatch),json={'request_type':'erasure-request'})
    assert r.status_code==200
    assert not r.json()['fulfillment_authorized'] and not r.json()['deleted']

def test_tenant_mismatch(monkeypatch):
    h=headers(monkeypatch);h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.get('/v1/privacy-governance/status',headers=h).status_code==403

def test_tenant_allowlist(monkeypatch):
    h=headers(monkeypatch);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/privacy-governance/status',headers=h).status_code==403

def test_role_denied(monkeypatch):
    assert client.get('/v1/privacy-governance/status',headers=headers(monkeypatch,'viewer')).status_code==403

def test_delete_consent_commit_blocked_even_with_flags(monkeypatch):
    h=headers(monkeypatch)
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1');monkeypatch.setenv('SCEC_OUTBOUND_ENABLED','1');monkeypatch.setenv('SCEC_DELETION_ENABLED','1')
    for route in ('delete','consent-commit','commit'):
        assert client.post('/v1/privacy-governance/'+route,headers=h).status_code==503

def test_extra_personal_fields_rejected(monkeypatch):
    h=headers(monkeypatch)
    assert client.post('/v1/privacy-governance/policy-preview',headers=h,json={'records':[sample(email='private@example.com')],'evaluation_day':'2026-10-12'}).status_code==422

def test_bad_category_and_calendar(monkeypatch):
    h=headers(monkeypatch)
    for item in (sample(channel='unknown'),sample(collected_day='2026-02-30')):
        assert client.post('/v1/privacy-governance/policy-preview',headers=h,json={'records':[item],'evaluation_day':'2026-10-12'}).status_code==422

def test_batch_limits(monkeypatch):
    h=headers(monkeypatch)
    for records in ([],[sample()]*51):
        assert client.post('/v1/privacy-governance/policy-preview',headers=h,json={'records':records,'evaluation_day':'2026-10-12'}).status_code==422

def test_preview_stable_without_raw_data():
    batch=Batch(records=[GovernanceItem(**sample())],evaluation_day=date(2026,10,12))
    r=compute(batch)
    assert r==compute(batch) and digest(r)==digest(compute(batch))
    assert 'records' not in r and not r['deleted']

def test_hold_and_missing_retention():
    batch=Batch(records=[GovernanceItem(**sample(deletion_hold=True,retention_days=None,collected_day=None))],evaluation_day=date(2026,10,12))
    r=compute(batch)
    assert r['review_flag_counts']['hold-review']==1
    assert r['review_flag_counts']['retention-insufficient-metadata']==1
