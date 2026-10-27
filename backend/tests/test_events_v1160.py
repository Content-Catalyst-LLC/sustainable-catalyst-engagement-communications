import time
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.events_v1160 import Speaker, Event, preview_event, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001'
OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production'

def speaker(**changes):
    return Speaker(**{**dict(synthetic=True,organization_id=ORG,speaker_ref='synthetic:00000000-0000-0000-0000-000000000003',attribution='Synthetic Speaker',privacy_reviewed=True,attribution_reviewed=True),**changes})

def event(**changes):
    return Event(**{**dict(synthetic=True,organization_id=ORG,event_ref='event:fixture',revision=0,kind='webinar',title='Synthetic webinar',description='Synthetic research discussion',canonical_url='https://example.org/event',starts_at='2026-11-01T01:30:00-05:00',ends_at='2026-11-01T01:30:00-06:00',updated_at='2026-10-27T00:00:00Z',timezone_name='America/Chicago',lifecycle='scheduled',source_refs=['source:fixture'],speakers=[speaker()],editorial_reviewed=True,rights_reviewed=True,privacy_reviewed=True),**changes})

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_EVENTS_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound');monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-event-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_dst_fallback_has_positive_duration_in_utc():
    r=preview_event(event(),ORG);ics=r['ics_preview']
    assert 'DTSTART:20261101T063000Z\r\n' in ics and 'DTEND:20261101T073000Z\r\n' in ics
    assert all(r[k] is False for k in DISABLED)
    assert len(r['live_acceptance_gates_pending'])==7
    for key in ['calendar_writes_enabled','registration_capture_enabled','invitations_enabled']:assert r[key] is False
    assert 'ATTENDEE' not in ics and 'ORGANIZER' not in ics and 'METHOD' not in ics and 'VALARM' not in ics


def test_cancel_update_preserves_uid_and_advances_sequence():
    original=preview_event(event(),ORG)
    cancelled=preview_event(event(revision=1,lifecycle='cancelled',change_notice='Synthetic cancellation'),ORG)
    assert original['event_uid']==cancelled['event_uid']
    assert 'STATUS:CANCELLED' in cancelled['ics_preview'] and 'SEQUENCE:1' in cancelled['ics_preview']
    assert original['sha256']!=cancelled['sha256']
    updated=preview_event(event(revision=2,change_notice='Synthetic update'),ORG)
    assert updated['event_uid']==original['event_uid'] and 'Notice: Synthetic update' in updated['ics_preview'].replace('\r\n ','')


@pytest.mark.parametrize('changes',[{'starts_at':'2026-03-08T02:30:00-06:00'},{'starts_at':'2026-11-01T01:30:00-04:00'},{'ends_at':'2026-11-01T00:30:00-05:00'},{'starts_at':'2026-11-01T01:30:00'},{'updated_at':'2026-10-27T00:00:00.1Z'},{'timezone_name':'Missing/Zone'},{'revision':1},{'revision':True},{'lifecycle':'cancelled'},{'title':'Bad\nATTENDEE:private@example.org'},{'email':'private@example.org'}])
def test_invalid_schedule_and_injection(changes):
    with pytest.raises(ValidationError):event(**changes)


@pytest.mark.parametrize('gate',['editorial_reviewed','rights_reviewed','privacy_reviewed'])
def test_event_reviews_fail_closed(gate):
    assert preview_event(event(**{gate:False}),ORG)['ics_preview'] is None
    with pytest.raises(ValidationError):event(**{gate:'yes'})


@pytest.mark.parametrize('gate',['privacy_reviewed','attribution_reviewed'])
def test_speaker_reviews_fail_closed(gate):
    assert preview_event(event(speakers=[speaker(**{gate:False})]),ORG)['ics_preview'] is None


def test_draft_suppressed_and_duplicate_cross_tenant():
    assert preview_event(event(lifecycle='draft'),ORG)['ics_preview'] is None
    assert preview_event(event(suppressed=True),ORG)['ics_preview'] is None
    with pytest.raises(ValidationError):event(speakers=[speaker(),speaker()])
    with pytest.raises(ValidationError):event(speakers=[speaker(organization_id=OTHER)])
    with pytest.raises(ValueError):preview_event(event(),OTHER)


def test_utf8_octet_folding_and_escaped_text():
    p=event(title='Synthetic '+('é'*70)+',;\\',description='Synthetic '+('界'*120))
    ics=preview_event(p,ORG)['ics_preview']
    assert all(len(line.encode())<=75 for line in ics.split('\r\n'))
    unfolded=ics.replace('\r\n ','')
    assert 'SUMMARY:Synthetic '+('é'*70)+r'\,\;\\' in unfolded
    assert unfolded.count('BEGIN:VEVENT')==1 and unfolded.count('END:VEVENT')==1
    assert '\n' not in ics.replace('\r\n','')


def test_http_scope_and_private_errors(client,monkeypatch):
    url='/v1/events/status'
    assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    assert client.get(url,headers=headers(OTHER)).status_code==403
    data=event().model_dump(mode='json');assert client.post('/v1/events/preview',headers=headers(),json=data).status_code==200
    data['description']='private@example.org'
    r=client.post('/v1/events/preview',headers=headers(),json=data)
    assert r.status_code==422 and data['description'] not in r.text
    monkeypatch.setenv('SCEC_EVENTS_STAGING_ENABLED','0')
    assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_live_event_operation(client,action):
    assert client.post('/v1/events/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_dangerous_flags_block(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1')
    assert client.get('/v1/events/status',headers=headers()).status_code==503
