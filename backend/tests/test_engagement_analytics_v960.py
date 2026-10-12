from uuid import uuid4
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.engagement_analytics_v960 import AnalyticsBatch,AggregateEvent,aggregate,fingerprint
client=TestClient(app)

def auth(monkeypatch,role='administrator'):
    org=uuid4();secret='analytics-staging-test-signing-123456789'
    monkeypatch.setenv('SCEC_ANALYTICS_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',secret)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    token=mint_token(subject='test',organization_id=org,roles={role},expires_at=int(time.time())+300,secret=secret)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':str(org)}

def event(**kwargs):
    return {'channel':'support','stage':'received','category':'bug','severity':'high', 'escalation_requested':True}|kwargs

def test_disabled_default(monkeypatch):
    monkeypatch.delenv('SCEC_ANALYTICS_STAGING_ENABLED',raising=False)
    assert client.get('/v1/engagement-analytics/status').status_code in (401,503)
def test_token_required(monkeypatch):
    monkeypatch.setenv('SCEC_ANALYTICS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    assert client.get('/v1/engagement-analytics/status').status_code==401
def test_bound_required(monkeypatch):
    monkeypatch.setenv('SCEC_ANALYTICS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert client.get('/v1/engagement-analytics/status').status_code==503
def test_status(monkeypatch):
    r=client.get('/v1/engagement-analytics/status',headers=auth(monkeypatch)); assert r.status_code==200,r.text
    assert r.json()['outbound_enabled'] is False and r.json()['writes_enabled'] is False
def test_report_aggregate(monkeypatch):
    data=[event(),event(channel='contact',severity='none',stage='resolved',escalation_requested=False,communication_eligible=True)]
    r=client.post('/v1/engagement-analytics/report-preview',headers=auth(monkeypatch),json={'events':data})
    assert r.status_code==200,r.text
    d=r.json()['report']
    assert d['record_count']==2 and d['counts']['channel']=={'contact':1,'support':1}
    assert d['resolved_or_closed_count']==1 and d['escalation_count']==1
    assert d['persisted'] is False and d['personal_data_included'] is False
    assert r.json()['deterministic_sha256']==fingerprint(d)
def test_funnel_not_claim_conversion(monkeypatch):
    r=client.post('/v1/engagement-analytics/funnel-preview',headers=auth(monkeypatch),json={'events':[event(),event(stage='closed')]})
    assert r.status_code==200 and 'not linked trajectories' in r.json()['note']
def test_cross_tenant_denied(monkeypatch):
    h=auth(monkeypatch); h['X-SCEC-Organization-ID']=str(uuid4())
    assert client.get('/v1/engagement-analytics/status',headers=h).status_code==403
def test_allowlist_denied(monkeypatch):
    h=auth(monkeypatch); monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    assert client.get('/v1/engagement-analytics/status',headers=h).status_code==403
def test_viewer_denied(monkeypatch):
    assert client.get('/v1/engagement-analytics/status',headers=auth(monkeypatch,'viewer')).status_code==403
def test_advisor_allowed(monkeypatch):
    assert client.get('/v1/engagement-analytics/status',headers=auth(monkeypatch,'advisor')).status_code==200
def test_export_commit_blocked_even_with_flags(monkeypatch):
    h=auth(monkeypatch);monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1');monkeypatch.setenv('SCEC_OUTBOUND_ENABLED','1')
    for route in ('export','commit'):
        assert client.post('/v1/engagement-analytics/'+route,headers=h).status_code==503
def test_reject_sensitive_arbitrary_fields(monkeypatch):
    h=auth(monkeypatch)
    payload=event(email='private@example.test')
    r=client.post('/v1/engagement-analytics/report-preview',headers=h,json={'events':[payload]})
    assert r.status_code==422
    assert 'private@example.test' not in r.text or r.status_code==422
def test_invalid_dimensions_and_dates(monkeypatch):
    h=auth(monkeypatch)
    for bad in (event(channel='secret'),event(occurred_day='2026-02-30')):
        assert client.post('/v1/engagement-analytics/report-preview',headers=h,json={'events':[bad]}).status_code==422
def test_empty_and_oversized_batch(monkeypatch):
    h=auth(monkeypatch)
    for records in ([],[event()]*101):
        assert client.post('/v1/engagement-analytics/report-preview',headers=h,json={'events':records}).status_code==422
def test_determinism_and_no_raw_records():
    batch=AnalyticsBatch(events=[AggregateEvent(**event())])
    result=aggregate(batch)
    assert result==aggregate(batch)
    assert fingerprint(result)==fingerprint(aggregate(batch))
    assert 'events' not in result and 'email' not in result
