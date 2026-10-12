from uuid import uuid4
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.support_intelligence_v930 import CasePreview,analyze

client=TestClient(app)
def headers(monkeypatch, role='contact_editor'):
    org=uuid4();secret='support-intelligence-local-secret-123456789012345'
    monkeypatch.setenv('SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='local-test',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}
def sample(**kw):
    return {**dict(subject='Dataset download fails',description='An error appears when downloading the dataset from the library.',source='staging-test',severity='medium'),**kw}

def test_closed_by_default(monkeypatch):
    monkeypatch.delenv('SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED',raising=False)
    assert client.get('/v1/support-intelligence/status').status_code in (401,503)
def test_missing_auth(monkeypatch):
    monkeypatch.setenv('SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.post('/v1/support-intelligence/case-preview',json=sample()).status_code==401
def test_bound_identity_required(monkeypatch):
    monkeypatch.setenv('SCEC_SUPPORT_INTELLIGENCE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/support-intelligence/status').status_code==503
def test_preview_safe(monkeypatch):
    h=headers(monkeypatch);r=client.post('/v1/support-intelligence/case-preview',headers=h,json=sample(description='My email private@example.org, and the application throws a crash error.'))
    assert r.status_code==200,r.text
    assert r.json()['persisted'] is False
    assert r.json()['analysis']['category']=='bug'
    assert 'private@example.org' not in r.text
    assert 'download' not in r.text
    assert r.json()['analysis']['human_review_required']
def test_summary_counts(monkeypatch):
    h=headers(monkeypatch)
    r=client.post('/v1/support-intelligence/summary-preview',headers=h,json={'cases':[sample(),sample(security_concern=True,severity='critical')]})
    assert r.status_code==200,r.text
    assert r.json()['count']==2
    assert r.json()['persisted'] is False
    assert r.json()['escalation_counts']['human-security-review']==1
def test_cross_tenant_denied(monkeypatch):
    h=headers(monkeypatch);h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.post('/v1/support-intelligence/case-preview',headers=h,json=sample()).status_code==403
def test_allowlist_denied(monkeypatch):
    h=headers(monkeypatch);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/support-intelligence/status',headers=h).status_code==403
def test_viewer_denied(monkeypatch):
    h=headers(monkeypatch,role='viewer')
    assert client.get('/v1/support-intelligence/status',headers=h).status_code==403
def test_write_immutable(monkeypatch):
    h=headers(monkeypatch);monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    assert client.post('/v1/support-intelligence/commit',headers=h,json=sample()).status_code==503
def test_schema_validation(monkeypatch):
    h=headers(monkeypatch)
    for bad in (sample(subject='x'),sample(category='not-real'),sample(severity='ultra'),sample(affected_users=-1),sample(current_status='wrong'),sample(internal=True)):
        assert client.post('/v1/support-intelligence/case-preview',headers=h,json=bad).status_code==422
    assert client.post('/v1/support-intelligence/summary-preview',headers=h,json={'cases':[sample()]*26}).status_code==422
def test_transition_and_determinism():
    case=CasePreview(**sample(current_status='triaged',proposed_status='closed'))
    assert analyze(case)['transition_valid'] is False
    assert analyze(case)==analyze(case)
    assert analyze(CasePreview(**sample(current_status='triaged',proposed_status='in-progress')))['transition_valid'] is True
