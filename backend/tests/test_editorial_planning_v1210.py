import hashlib
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.communication_objects_v1200 import make_node, CommunicationObject, EvidencePointer, preview_object
from app.editorial_planning_v1210 import LaunchWindow, Blackout, EditorialPlan, simulate_plan, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production';SYNTH={'synthetic':True,'organization_id':ORG}

def communication():
    root=make_node(node_ref='node:research',kind='research',research_ref='research:fixture',research_revision='r1',artifact_ref='research:fixture',artifact_revision='r1',source_release='11.0.0',source_hash_kind='source-manifest',source_digest=hashlib.sha256(b'synthetic fixture').hexdigest(),source_refs=('source:fixture',),**SYNTH)
    return CommunicationObject(communication_ref='communication:fixture',revision='r1',root_node_ref=root.node_ref,nodes=(root,),**SYNTH)

def window(**changes):
    root=communication().nodes[0]
    return LaunchWindow(**{**dict(window_ref='window:one',evidence=EvidencePointer(node_ref=root.node_ref,evidence_sha256=root.evidence_sha256,**SYNTH),starts_at='2026-11-01T12:00:00Z',ends_at='2026-11-01T13:00:00Z',timezone_name='UTC',embargo_reviewed=True,editorial_reviewed=True,**SYNTH),**changes})

def plan(**changes):
    obj=communication()
    return EditorialPlan(**{**dict(plan_ref='plan:fixture',revision='r1',communication=obj,communication_sha256=preview_object(obj,ORG)['sha256'],as_of='2026-10-27T00:00:00Z',windows=(window(),),**SYNTH),**changes})

def result(**changes):return simulate_plan(plan(**changes),ORG)

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_CALENDAR_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-calendar-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_valid_dependency_plan_is_never_scheduled():
    first=window();second=window(window_ref='window:two',starts_at='2026-11-01T13:00:00Z',ends_at='2026-11-01T14:00:00Z',depends_on=('window:one',))
    r=result(windows=(second,first))
    assert all(w['eligible_for_plan_only'] for w in r['windows'])
    assert all(r[k] is False for k in DISABLED)
    for k in ['cron_enabled','calendar_writes_enabled','notifications_enabled','automatic_rescheduling_enabled']:assert r[k] is False
    assert len(r['live_acceptance_gates_pending'])==7
    assert r==result(windows=(first,second))


def test_dst_fallback_window_is_compared_in_utc():
    w=window(starts_at='2026-11-01T01:30:00-05:00',ends_at='2026-11-01T01:30:00-06:00',timezone_name='America/Chicago')
    r=result(windows=(w,))['windows'][0]
    assert r['eligible_for_plan_only'] and r['proposed_start_utc']=='2026-11-01T06:30:00+00:00' and r['proposed_end_utc']=='2026-11-01T07:30:00+00:00'


@pytest.mark.parametrize('changes,reason',[({'embargo_reviewed':False},'embargo-review-required'),({'editorial_reviewed':False},'editorial-review-required'),({'embargo_until':'2026-11-01T12:00:01Z'},'embargo-active')])
def test_review_and_embargo_denial(changes,reason):
    r=result(windows=(window(**changes),))['windows'][0];assert not r['eligible_for_plan_only'] and reason in r['review_flags']


def test_blackout_overlap_not_touching_boundaries():
    b=Blackout(blackout_ref='blackout:fixture',starts_at='2026-11-01T12:30:00Z',ends_at='2026-11-01T13:30:00Z',timezone_name='UTC',**SYNTH)
    assert 'blackout-overlap' in result(blackouts=(b,))['windows'][0]['review_flags']
    b=Blackout(blackout_ref='blackout:fixture',starts_at='2026-11-01T13:00:00Z',ends_at='2026-11-01T14:00:00Z',timezone_name='UTC',**SYNTH)
    assert result(blackouts=(b,))['windows'][0]['eligible_for_plan_only']
    assert 'window-in-past' in result(as_of='2026-11-01T12:00:01Z')['windows'][0]['review_flags']


def test_dependency_timing_and_denial_propagation():
    first=window(editorial_reviewed=False)
    second=window(window_ref='window:two',depends_on=('window:one',))
    flags=result(windows=(first,second))['windows'][1]['review_flags']
    assert 'dependency-ineligible' in flags and 'dependency-not-finished' in flags


def test_missing_cycle_and_stale_references():
    with pytest.raises(ValidationError):plan(windows=(window(depends_on=('window:missing',)),))
    with pytest.raises(ValidationError):plan(windows=(window(depends_on=('window:one',)),))
    with pytest.raises(ValidationError):plan(windows=(window(depends_on=('window:two',)),window(window_ref='window:two',depends_on=('window:one',))))
    with pytest.raises(ValidationError):plan(communication_sha256='a'*64)
    with pytest.raises(ValidationError):plan(windows=(window(evidence=EvidencePointer(node_ref='node:research',evidence_sha256='a'*64,**SYNTH)),))


@pytest.mark.parametrize('changes',[{'starts_at':'2026-03-08T02:30:00-06:00','timezone_name':'America/Chicago'},{'starts_at':'2026-11-01T12:00:00'},{'ends_at':'2026-11-01T11:00:00Z'},{'timezone_name':'Missing/Zone'},{'editorial_reviewed':'yes'},{'email':'private@example.org'}])
def test_invalid_or_unsafe_windows(changes):
    with pytest.raises(ValidationError):window(**changes)


def test_tenant_and_duplicate_windows():
    with pytest.raises(ValidationError):window(organization_id=OTHER)
    with pytest.raises(ValidationError):plan(windows=(window(),window()))
    with pytest.raises(ValueError):simulate_plan(plan(),OTHER)


def test_hash_changes_with_constraints():
    assert result()['sha256']!=result(windows=(window(embargo_reviewed=False),))['sha256']
    assert result()['sha256']!=result(revision='r2')['sha256']


def test_http_tenant_role_default_and_error_redaction(client,monkeypatch):
    url='/v1/editorial-planning/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=plan().model_dump(mode='json');assert client.post('/v1/editorial-planning/preview',headers=headers(),json=data).status_code==200
    data['email']='private@example.org';r=client.post('/v1/editorial-planning/preview',headers=headers(),json=data);assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_CALENDAR_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_cron_calendar_or_delivery(client,action):
    assert client.post('/v1/editorial-planning/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/editorial-planning/status',headers=headers()).status_code==503
