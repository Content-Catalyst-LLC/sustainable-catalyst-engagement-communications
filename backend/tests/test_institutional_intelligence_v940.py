from uuid import uuid4
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.institutional_intelligence_v940 import RelationshipPreview,analyze

client=TestClient(app)
def headers(monkeypatch,role='advisor'):
    org=uuid4(); secret='institutional-staging-local-secret-1234567890'
    monkeypatch.setenv('SCEC_INSTITUTIONAL_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='institutional-test',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}
def sample(**kwargs):
    return {**dict(organization_name='Community Research Group',inquiry_title='Research collaboration inquiry',description='We are interested in a joint research publication and data methods.',source='staging-test'),**kwargs}
def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SCEC_INSTITUTIONAL_STAGING_ENABLED',raising=False)
    assert client.get('/v1/institutional-intelligence/status').status_code in (401,503)
def test_no_auth(monkeypatch):
    monkeypatch.setenv('SCEC_INSTITUTIONAL_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.post('/v1/institutional-intelligence/relationship-preview',json=sample()).status_code==401
def test_bound_required(monkeypatch):
    monkeypatch.setenv('SCEC_INSTITUTIONAL_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/institutional-intelligence/status').status_code==503
def test_safe_preview(monkeypatch):
    h=headers(monkeypatch)
    r=client.post('/v1/institutional-intelligence/relationship-preview',headers=h,json=sample(description='Joint research study requested by private@example.org.'))
    assert r.status_code==200,r.text
    assert r.json()['analysis']['relationship_type']=='research-partnership'
    assert r.json()['analysis']['approval_effective'] is False
    assert r.json()['persisted'] is False
    assert 'private@example.org' not in r.text
    assert 'Research Group' not in r.text
def test_portfolio(monkeypatch):
    h=headers(monkeypatch)
    r=client.post('/v1/institutional-intelligence/portfolio-preview',headers=h,json={'inquiries':[sample(),sample(data_sharing_requested=True)]})
    assert r.status_code==200,r.text
    assert r.json()['count']==2
    assert r.json()['review_flag_counts']['data-sharing-review']==1
def test_cross_tenant(monkeypatch):
    h=headers(monkeypatch);h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.get('/v1/institutional-intelligence/status',headers=h).status_code==403
def test_allowlist(monkeypatch):
    h=headers(monkeypatch);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/institutional-intelligence/status',headers=h).status_code==403
def test_viewer_denied(monkeypatch):
    h=headers(monkeypatch,role='viewer')
    assert client.get('/v1/institutional-intelligence/status',headers=h).status_code==403
def test_commit_remains_disabled_even_if_persistence_enabled(monkeypatch):
    h=headers(monkeypatch);monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    assert client.post('/v1/institutional-intelligence/commit',headers=h,json=sample()).status_code==503
def test_validation(monkeypatch):
    h=headers(monkeypatch)
    for bad in [dict(sample(),organization_name='a'),dict(sample(),relationship_type='invented'),dict(sample(),proposed_stage='invalid'),dict(sample(),source='wordpress-feedback'),dict(sample(),extra='x')]:
        assert client.post('/v1/institutional-intelligence/relationship-preview',headers=h,json=bad).status_code==422
    assert client.post('/v1/institutional-intelligence/portfolio-preview',headers=h,json={'inquiries':[sample()]*26}).status_code==422
def test_transitions_and_determinism():
    r=RelationshipPreview(**sample(current_stage='review',proposed_stage='approved',conflict_of_interest_flag=True,human_approval_recorded=True))
    a=analyze(r)
    assert a['transition_valid'] is True
    assert a['approval_effective'] is False
    assert a['review_flags']==['conflict-of-interest-review']
    assert analyze(r)==a
    assert analyze(RelationshipPreview(**sample(current_stage='inquiry',proposed_stage='approved')))['transition_valid'] is False
