from uuid import uuid4
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.communications_intelligence_v950 import NotificationPlan,evaluate
client=TestClient(app)

def auth(monkeypatch,role='administrator'):
    org=uuid4();secret='comms-local-only-signing-secret-123456789'
    monkeypatch.setenv('SCEC_COMMUNICATIONS_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='test',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}
def sample(**overrides):
    return dict(event_type='support-update',template='case-update',requested_channels=['email'],consent_recorded=True,consent_scope=['email'],recipient_verified=True,reference='staged-001')|overrides

def test_default_disabled(monkeypatch):
    monkeypatch.delenv('SCEC_COMMUNICATIONS_STAGING_ENABLED',raising=False)
    assert client.get('/v1/communications-intelligence/status').status_code in (401,503)
def test_requires_token(monkeypatch):
    monkeypatch.setenv('SCEC_COMMUNICATIONS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.post('/v1/communications-intelligence/plan-preview',json=sample()).status_code==401
def test_bound_required(monkeypatch):
    monkeypatch.setenv('SCEC_COMMUNICATIONS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/communications-intelligence/status').status_code==503
def test_status(monkeypatch):
    r=client.get('/v1/communications-intelligence/status',headers=auth(monkeypatch));assert r.status_code==200,r.text
    assert r.json()['outbound_enabled'] is False
    assert r.json()['writes_enabled'] is False
def test_plan_eligibility_never_authorizes_delivery(monkeypatch):
    r=client.post('/v1/communications-intelligence/plan-preview',headers=auth(monkeypatch),json=sample())
    assert r.status_code==200,r.text
    a=r.json()['analysis'];assert a['eligible_for_human_review'] is True
    assert a['delivery_authorized'] is False and a['messages_sent']==0 and a['queued'] is False
def test_no_consent_no_recipient_and_sensitive(monkeypatch):
    r=client.post('/v1/communications-intelligence/plan-preview',headers=auth(monkeypatch),json=sample(consent_recorded=False,recipient_verified=False,sensitive_content=True))
    assert r.status_code==200
    assert set(r.json()['analysis']['reasons']) >= {'consent-required','recipient-verification-required','sensitive-content-review'}
def test_no_pii_echo(monkeypatch):
    h=auth(monkeypatch);payload=sample(reference='private-test-reference')
    r=client.post('/v1/communications-intelligence/plan-preview',headers=h,json=payload)
    assert r.status_code==200 and 'private-test-reference' not in r.text
def test_audit(monkeypatch):
    h=auth(monkeypatch)
    r=client.post('/v1/communications-intelligence/audit-preview',headers=h,json={'plans':[sample(),sample(consent_recorded=False)]})
    assert r.status_code==200,r.text
    assert r.json()['count']==2 and r.json()['sent']==0 and r.json()['review_counts']=={'eligible':1,'blocked':1}
def test_cross_tenant_denied(monkeypatch):
    h=auth(monkeypatch);h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.get('/v1/communications-intelligence/status',headers=h).status_code==403
def test_allowlist_denied(monkeypatch):
    h=auth(monkeypatch);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/communications-intelligence/status',headers=h).status_code==403
def test_viewer_denied(monkeypatch):
    assert client.get('/v1/communications-intelligence/status',headers=auth(monkeypatch,'viewer')).status_code==403
def test_send_and_commit_always_disabled(monkeypatch):
    h=auth(monkeypatch);monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1');monkeypatch.setenv('SCEC_OUTBOUND_ENABLED','1')
    for route in ('send','commit'):
        assert client.post('/v1/communications-intelligence/'+route,headers=h,json=sample()).status_code==503
def test_strict_fields_and_batch_limit(monkeypatch):
    h=auth(monkeypatch)
    assert client.post('/v1/communications-intelligence/plan-preview',headers=h,json=sample(surprise='x')).status_code==422
    assert client.post('/v1/communications-intelligence/audit-preview',headers=h,json={'plans':[sample()]*26}).status_code==422
def test_invalid_event_channel_consent():
    a=evaluate(NotificationPlan(**sample(event_type='unknown',requested_channels=['push'],consent_scope=[])))
    assert 'unsupported-event' in a['reasons'] and 'unsupported-channel' in a['reasons'] and 'channel-consent-missing' in a['reasons']
def test_deterministic():
    payload=NotificationPlan(**sample(escalation_requested=True))
    assert evaluate(payload)==evaluate(payload)
    assert evaluate(payload)['delivery_authorized'] is False
