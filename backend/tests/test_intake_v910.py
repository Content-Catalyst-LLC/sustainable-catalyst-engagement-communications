from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
import time

client=TestClient(app)

def auth(monkeypatch, role='contact_editor', tenant=None):
    tenant=tenant or uuid4()
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY','test-secret-for-engagement-intake-staging-123456')
    monkeypatch.setenv('SCEC_INTAKE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(tenant))
    token=mint_token(subject='staging-adapter',organization_id=tenant,roles={role},expires_at=int(time.time())+300,secret='test-secret-for-engagement-intake-staging-123456')
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(tenant)}

def payload(kind='contact'):
    return dict(kind=kind,source='wordpress-'+kind,name='Jane Example',email='Jane@Example.org',subject='Inquiry',message='Please respond',consent_to_reply=True)

def test_staging_off_by_default(monkeypatch):
    monkeypatch.delenv('SCEC_INTAKE_STAGING_ENABLED',raising=False)
    r=client.get('/v1/intake/status')
    assert r.status_code in (401,503)

def test_no_auth_is_denied(monkeypatch):
    monkeypatch.setenv('SCEC_INTAKE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.post('/v1/intake/preview',json=payload()).status_code==401

def test_legacy_mode_denied(monkeypatch):
    monkeypatch.setenv('SCEC_INTAKE_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/intake/status').status_code==503

def test_status_and_preview(monkeypatch):
    headers=auth(monkeypatch)
    assert client.get('/v1/intake/status',headers=headers).json()['writes_enabled'] is False
    for kind in ('contact','feedback'):
        r=client.post('/v1/intake/preview',json=payload(kind),headers=headers)
        assert r.status_code==200,r.text
        assert r.json()['persisted'] is False
        assert 'Jane' not in r.text and 'example.org' not in r.text

def test_commit_always_denied(monkeypatch):
    headers=auth(monkeypatch)
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    assert client.post('/v1/intake/commit',headers=headers,json=payload()).status_code==503

def test_tenant_spoofing(monkeypatch):
    headers=auth(monkeypatch)
    headers['X-SCEC-Organization-ID']=str(uuid4())
    assert client.post('/v1/intake/preview',headers=headers,json=payload()).status_code==403

def test_role_denied(monkeypatch):
    headers=auth(monkeypatch,role='viewer')
    assert client.post('/v1/intake/preview',headers=headers,json=payload()).status_code==403

def test_org_allowlist_denied(monkeypatch):
    headers=auth(monkeypatch)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.post('/v1/intake/preview',headers=headers,json=payload()).status_code==403

def test_invalid_source(monkeypatch):
    headers=auth(monkeypatch)
    assert client.post('/v1/intake/preview',headers=headers,json={**payload(),'source':'wordpress-feedback'}).status_code==422

def test_invalid_and_extra_fields(monkeypatch):
    headers=auth(monkeypatch)
    assert client.post('/v1/intake/preview',headers=headers,json={**payload(),'email':'nope'}).status_code==422
    assert client.post('/v1/intake/preview',headers=headers,json={**payload(),'is_admin':True}).status_code==422
    assert client.post('/v1/intake/preview',headers=headers,json={**payload(),'message':'x'*9000}).status_code==422

def test_no_legacy_wordpress_edits():
    from pathlib import Path
    source=Path(__file__).resolve().parents[2]
    assert (source/'wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php').exists()
