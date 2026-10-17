from pathlib import Path
from uuid import uuid4
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.delivery_infrastructure_v1070 import DeliveryPreview,delivery_assessment,safety_state,CHANNELS,RETRY_SECONDS
TENANT=str(uuid4())
def payload(**kw):
    data=dict(reference='synthetic-case',channel='email',template='acknowledgment',idempotency_key='synthetic-key-001')
    data.update(kw)
    return DeliveryPreview(**data)
@pytest.mark.parametrize('channel',CHANNELS)
def test_preview_never_sends(channel):
    r=delivery_assessment(payload(channel=channel),TENANT)
    assert r['messages_sent']==0 and not r['delivery_authorized'] and not r['queued'] and not r['persisted']
    assert r['transport_adapters']==[] and not r['production_certified']
@pytest.mark.parametrize('field,expected', [('recipient_verified','recipient-unverified'),('consent_recorded','channel-consent-not-proven'),('human_approval_recorded','human-approval-missing')])
def test_required_review_gates(field,expected):
    kwargs=dict(recipient_verified=True,consent_recorded=True,consent_channel='email',human_approval_recorded=True)
    kwargs[field]=False
    assert expected in delivery_assessment(payload(**kwargs),TENANT)['blockers']
@pytest.mark.parametrize('field,expected', [('suppressed','suppressed'),('unsubscribed','unsubscribed'),('contains_sensitive_content','sensitive-content-review')])
def test_suppression_and_review(field,expected):
    assert expected in delivery_assessment(payload(**{field:True}),TENANT)['blockers']
def test_consent_channel_must_match():
    assert 'channel-consent-not-proven' in delivery_assessment(payload(consent_recorded=True,consent_channel='sms'),TENANT)['blockers']
def test_nominal_preview_still_never_authorizes():
    r=delivery_assessment(payload(recipient_verified=True,consent_recorded=True,consent_channel='email',human_approval_recorded=True),TENANT)
    assert r['eligible_for_human_review'] and not r['delivery_authorized'] and not r['queued']
@pytest.mark.parametrize('attempt,delay',[(0,60),(1,300),(2,1800),(3,None),(4,None)])
def test_retry_preview(attempt,delay):
    r=delivery_assessment(payload(simulated_retry_attempt=attempt),TENANT)
    assert r['next_retry_delay_seconds_preview']==delay
    if attempt==4:assert 'retry-budget-exhausted' in r['blockers']
def test_deterministic_tenant_bound_hash():
    a=delivery_assessment(payload(),TENANT)
    b=delivery_assessment(payload(),TENANT)
    c=delivery_assessment(payload(idempotency_key='synthetic-key-002'),TENANT)
    assert a['synthetic_evidence_sha256']==b['synthetic_evidence_sha256']!=c['synthetic_evidence_sha256']
    assert len(a['synthetic_evidence_sha256'])==64
    assert 'synthetic-key-001' not in repr(a)
def test_bad_tenant():
    with pytest.raises(ValueError):delivery_assessment(payload(),TENANT.upper())
@pytest.mark.parametrize('extra',[{'email':'person@example.org'},{'message_body':'secret'},{'recipient_address':'test@example.org'}])
def test_pii_fields_rejected(extra):
    with pytest.raises(ValidationError):DeliveryPreview(**payload().model_dump(),**extra)
@pytest.mark.parametrize('field,value',[('channel','fax'),('template','unauthorized'),('simulated_retry_attempt',6),('idempotency_key','oops')])
def test_invalid_contract_fields(field,value):
    with pytest.raises(ValidationError):DeliveryPreview(**{**payload().model_dump(),field:value})
def test_flags_fail_closed(monkeypatch):
    for flag in ('SCEC_HUMAN_AUTH_ENABLED','SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):monkeypatch.setenv(flag,'0')
    assert safety_state()
    monkeypatch.setenv('SCEC_OUTBOUND_ENABLED','1')
    assert not safety_state()
@pytest.mark.parametrize('endpoint', ['/status','/contracts'])
def test_gated_get(monkeypatch,endpoint):
    monkeypatch.setenv('SCEC_DELIVERY_STAGING_ENABLED','0')
    assert TestClient(app).get('/v1/delivery-infrastructure'+endpoint).status_code in (401,503)
@pytest.mark.parametrize('endpoint', ['/preview','/send','/dispatch','/enqueue','/retry','/approve','/commit','/promote'])
def test_gated_post(monkeypatch,endpoint):
    monkeypatch.setenv('SCEC_DELIVERY_STAGING_ENABLED','0')
    assert TestClient(app).post('/v1/delivery-infrastructure'+endpoint,json={}).status_code in (401,422,503)
def test_transport_absent():
    code=(Path(__file__).resolve().parents[1]/'app/delivery_infrastructure_v1070.py').read_text()
    assert not any(s in code for s in ('smtplib','requests.post(', 'httpx.post(', 'psycopg.connect(', 'sqlite3.connect(', 'subprocess.run(', 'os.remove('))
