import time
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.audience_v1190 import AudienceEvent, MetricSource, AudienceBatch, aggregate_audience, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production'

def ref(number):return 'synthetic:'+str(UUID(int=number))

def event(number,kind='view',**changes):
    return AudienceEvent(**{**dict(synthetic=True,organization_id=ORG,event_ref=ref(number+(1000 if kind=='engage' else 0)),reader_ref=ref(number),object_ref='object:fixture',revision='r1',channel='embed',kind=kind,occurred_day='2026-10-27',source_ref='source:fixture'),**changes})

def batch(**changes):
    return AudienceBatch(**{**dict(synthetic=True,organization_id=ORG,events=[event(i) for i in range(1,6)],sources=[MetricSource(synthetic=True,organization_id=ORG,source_ref='source:fixture',edition='fixture-r1')]),**changes})

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_AUDIENCE_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-audience-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_distinct_readership_not_event_volume_and_no_id_output():
    p=batch(events=[event(i) for i in range(1,6)]+[event(i,'engage') for i in range(1,6)])
    r=aggregate_audience(p,ORG)
    assert r['rows']==[{'channel':'embed','distinct_synthetic_readers':5,'distinct_synthetic_engaged_readers':5,'descriptive_engagement_share':1.0}]
    assert all(r[k] is False for k in DISABLED)
    assert not r['tracking_enabled'] and not r['identity_export_enabled'] and r['historical_records_queried']==0
    assert len(r['live_acceptance_gates_pending'])==7
    assert all(e.reader_ref not in str(r) and e.event_ref not in str(r) for e in p.events)


def test_replayed_events_are_identical_evidence():
    p=batch();q=batch(events=[*p.events,*p.events])
    assert aggregate_audience(p,ORG)==aggregate_audience(q,ORG)
    data=p.model_dump();data['events'].reverse();assert aggregate_audience(p,ORG)==aggregate_audience(AudienceBatch(**data),ORG)
    data=p.events[0].model_dump();data['channel']='feed'
    with pytest.raises(ValidationError):batch(events=[*p.events,AudienceEvent(**data)])


def test_repeated_reader_does_not_inflate_threshold():
    r=aggregate_audience(batch(events=[event(i,reader_ref=ref(1)) for i in range(1,6)]),ORG)
    assert r['rows'] is None and r['suppression_applied']


@pytest.mark.parametrize('events',[[event(i) for i in range(1,5)],[event(i) for i in range(1,6)]+[event(1,'engage')],[event(i) for i in range(1,6)]+[event(6,channel='feed')]])
def test_small_cells_suppress_entire_table_without_residual_totals(events):
    r=aggregate_audience(batch(events=events),ORG)
    assert r['rows'] is None and r['suppression_applied']
    assert not {'total','event_count','reader_count','suppressed_channels'}.intersection(r)


@pytest.mark.parametrize('k',[0,1,4,51,True,'5'])
def test_threshold_cannot_be_downgraded_or_coerced(k):
    with pytest.raises(ValidationError):batch(minimum_group_size=k)


def test_orphan_engagement_and_provenance_fail_closed():
    with pytest.raises(ValidationError):batch(events=[event(1,'engage')])
    with pytest.raises(ValidationError):batch(events=[event(1,source_ref='source:missing')])
    with pytest.raises(ValidationError):batch(events=[event(1,organization_id=OTHER)])
    with pytest.raises(ValidationError):batch(sources=[])
    with pytest.raises(ValidationError):event(1,email='private@example.org')
    with pytest.raises(ValidationError):event(1,reader_ref='real-person@example.org')
    with pytest.raises(ValueError):aggregate_audience(batch(),OTHER)


def test_source_edition_and_threshold_are_evidence_bound():
    p=batch();original=aggregate_audience(p,ORG)
    data=p.model_dump();data['sources'][0]['edition']='fixture-r2'
    assert aggregate_audience(AudienceBatch(**data),ORG)['sha256']!=original['sha256']
    assert aggregate_audience(batch(minimum_group_size=6),ORG)['sha256']!=original['sha256']
    assert original['provenance'][0]['measurement_basis']=='synthetic-fixture'


def test_http_scope_and_private_validation(client,monkeypatch):
    url='/v1/audience-analytics/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=batch().model_dump(mode='json');assert client.post('/v1/audience-analytics/preview',headers=headers(),json=data).status_code==200
    data['events'][0]['email']='private@example.org';r=client.post('/v1/audience-analytics/preview',headers=headers(),json=data)
    assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_AUDIENCE_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_tracking_collection_or_export(client,action):
    assert client.post('/v1/audience-analytics/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_block(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/audience-analytics/status',headers=headers()).status_code==503
