import ast
import hashlib
import json
import time
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.newsletter_alerts_v1130 import (
    SubscriptionPreference, ResearchAlert, AlertPreview, compose, TOPICS,
    FREQUENCIES, CHANNELS, STATES, BLOCKED_ACTIONS, DANGER_FLAGS, EXTRA_DANGER_FLAGS,
)

ORG='00000000-0000-0000-0000-000000000001'
OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-test-key-never-a-production-credential'


def preference(**changes):
    value=dict(synthetic=True,organization_id=ORG,subscriber_ref='synthetic:'+str(uuid4()),
               topics=['climate-nature'],channels=['email'],consent=True,state='active-preview')
    value.update(changes)
    return SubscriptionPreference(**value)


def alert(**changes):
    value=dict(synthetic=True,organization_id=ORG,object_ref='research:example',revision='rev-1',
               headline='Synthetic research update',summary='Synthetic summary for offline review',
               source_refs=['source:example'],topics=['climate-nature'],review_state='approved-preview',
               privacy_reviewed=True,editorial_reviewed=True,source_integrity_reviewed=True,
               distribution_reviewed=True,rights_reviewed=True)
    value.update(changes)
    return ResearchAlert(**value)


def preview(**changes):
    value=dict(alert=alert(),preferences=[preference()]);value.update(changes)
    return AlertPreview(**value)


@pytest.fixture
def enabled(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_ALERTS_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)


def headers(organization=ORG,roles=('administrator',),expiry=None):
    token=mint_token(subject='synthetic-reviewer',organization_id=organization,roles=list(roles),
                     expires_at=int(time.time())+300 if expiry is None else expiry,secret=KEY)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':organization}


def test_contract_registry_and_current_health():
    assert len(TOPICS)==8 and len(STATES)==4
    assert TestClient(app).get('/health').json()=={'status':'ok','service':'engagement-communications',
          'version':'12.2.0','phase':'multichannel-campaign-composition-staging'}


@pytest.mark.parametrize('topic',list(TOPICS))
def test_each_topic_matches(topic):
    p=preview(alert=alert(topics=[topic]),preferences=[preference(topics=[topic])])
    assert compose(p,ORG)['preview_eligible_count']==1


@pytest.mark.parametrize('frequency',FREQUENCIES)
@pytest.mark.parametrize('channel',CHANNELS)
def test_frequency_and_channel_are_preview_types(frequency,channel):
    p=preview(frequency=frequency,channel=channel,preferences=[preference(frequency=frequency,channels=[channel])])
    result=compose(p,ORG)
    assert result['preview_eligible_count']==1 and not result['scheduled_delivery_enabled']


@pytest.mark.parametrize('field',['consent','email','recipient_email','phone','address','name','recipient_list','activate'])
def test_real_contact_and_activation_fields_rejected(field):
    if field=='consent':
        with pytest.raises(ValidationError):preference(consent='yes')
    else:
        with pytest.raises(ValidationError):preference(**{field:'private@example.org'})


@pytest.mark.parametrize('synthetic',[False,0,1,'true',None])
def test_synthetic_must_be_explicit_boolean(synthetic):
    with pytest.raises(ValidationError):preference(synthetic=synthetic)


@pytest.mark.parametrize('reference',['alice@example.org','+13125551212','alice','synthetic:00000000-0000-0000-0000-000000000000'])
def test_subscriber_identifiers_are_opaque(reference):
    with pytest.raises(ValidationError):preference(subscriber_ref=reference)


@pytest.mark.parametrize('state',['opted-out','suppressed'])
def test_opt_out_and_suppression(state):
    result=compose(preview(preferences=[preference(state=state)]),ORG)
    assert result['preview_eligible_count']==0 and state in result['excluded_synthetic_refs'][0]['reasons']


def test_missing_consent_defaults_closed():
    p=preference().model_dump();p.pop('consent');p=SubscriptionPreference(**p)
    result=compose(preview(preferences=[p]),ORG)
    assert not result['matched_synthetic_refs'] and 'missing-consent' in result['excluded_synthetic_refs'][0]['reasons']


@pytest.mark.parametrize('field',['privacy_reviewed','editorial_reviewed','source_integrity_reviewed','distribution_reviewed','rights_reviewed'])
def test_every_content_gate_is_required(field):
    result=compose(preview(alert=alert(**{field:False})),ORG)
    assert not result['review_complete_for_preview_only'] and result['preview_eligible_count']==0
    with pytest.raises(ValidationError):alert(**{field:'approved'})


@pytest.mark.parametrize('state',['draft','review','denied'])
def test_review_state_cannot_be_spoofed_by_review_booleans(state):
    assert compose(preview(alert=alert(review_state=state)),ORG)['preview_eligible_count']==0


def test_every_approval_still_cannot_deliver_or_publish():
    result=compose(preview(),ORG)
    assert result['review_complete_for_preview_only'] and result['preview_eligible_count']==1
    for field in ['publication_authorized','actual_publication_enabled','actual_syndication_enabled',
                  'subscription_activation_enabled','outbound_communications_enabled','scheduled_delivery_enabled',
                  'persisted','source_fetch_performed','human_login_enabled','deletion_enabled',
                  'federation_enabled','token_exchange_enabled','production_writes_enabled','production_certified']:
        assert result[field] is False
    assert result['review_gates']['production-acceptance'] is False
    assert len(result['live_acceptance_gates_pending'])==7


@pytest.mark.parametrize('changes',[{'topics':['energy-systems']},{'frequency':'daily'},{'channels':['in-app']}])
def test_segmentation_excludes_mismatches(changes):
    assert compose(preview(preferences=[preference(**changes)]),ORG)['preview_eligible_count']==0


def test_determinism_and_revision_provenance():
    a=preference(topics=['climate-nature','methods-data'],channels=['email','in-app']);b=preference()
    p=preview(preferences=[a,b]); first=compose(p,ORG)
    normalized=a.model_dump();normalized['topics'].reverse();normalized['channels'].reverse()
    reordered=preview(preferences=[b,SubscriptionPreference(**normalized)])
    assert first==compose(reordered,ORG)
    assert first['sha256']!=compose(preview(alert=alert(revision='rev-2'),preferences=[a,b]),ORG)['sha256']
    assert first['sha256']!=compose(preview(alert=alert(source_refs=['source:different']),preferences=[a,b]),ORG)['sha256']
    assert first['sha256']!=compose(preview(alert=alert(privacy_reviewed=False),preferences=[a,b]),ORG)['sha256']


def test_duplicates_and_cross_tenant_fixtures_rejected():
    p=preference()
    with pytest.raises(ValidationError):preview(preferences=[p,p])
    with pytest.raises(ValidationError):preview(preferences=[preference(organization_id=OTHER)])
    with pytest.raises(ValueError):compose(preview(),OTHER)
    with pytest.raises(ValueError):compose(preview(),'bad')
    with pytest.raises(ValidationError):alert(source_refs=['source:one','source:one'])
    with pytest.raises(ValidationError):preference(topics=['climate-nature','climate-nature'])


@pytest.mark.parametrize('text',['contact@example.org','+1 312 555 1234','<script>alert(1)</script>','https://internal.example/private'])
@pytest.mark.parametrize('field',['headline','summary'])
def test_contact_markup_and_url_content_rejected(field,text):
    with pytest.raises(ValidationError):alert(**{field:text})


@pytest.mark.parametrize('change',[{'topics':[]},{'topics':['unknown']},{'channels':[]},{'channels':['sms']},{'frequency':'hourly'},{'topics':list(TOPICS)*2}])
def test_preference_bounds(change):
    with pytest.raises(ValidationError):preference(**change)


@pytest.mark.parametrize('change',[{'headline':''},{'headline':'x'*181},{'summary':'x'*601},{'source_refs':[]},{'source_refs':['x@y.org']},{'revision':'x'*49},{'review_state':'published'}])
def test_alert_bounds(change):
    with pytest.raises(ValidationError):alert(**change)


def test_all_http_routes_default_disabled(monkeypatch):
    monkeypatch.setenv('SCEC_ALERTS_STAGING_ENABLED','0')
    c=TestClient(app)
    assert c.get('/v1/research-alerts/status').status_code in (401,503)
    assert c.post('/v1/research-alerts/preview',json=preview().model_dump()).status_code in (401,503)


def test_bound_authenticated_preview_and_status(enabled):
    assert enabled.get('/v1/research-alerts/status',headers=headers()).status_code==200
    response=enabled.post('/v1/research-alerts/preview',headers=headers(),json=preview().model_dump())
    assert response.status_code==200 and not response.json()['persisted']


@pytest.mark.parametrize('role',['viewer','contact_editor','advisor','approver','support_agent'])
def test_nonprivileged_roles_denied(enabled,role):
    assert enabled.get('/v1/research-alerts/status',headers=headers(roles=(role,))).status_code==403


def test_http_tenant_and_expiry_boundaries(enabled):
    assert enabled.get('/v1/research-alerts/status').status_code==401
    assert enabled.get('/v1/research-alerts/status',headers=headers(organization=OTHER)).status_code==403
    assert enabled.get('/v1/research-alerts/status',headers=headers(expiry=int(time.time())-10)).status_code==401
    h=headers();h['X-SCEC-Organization-ID']=OTHER
    assert enabled.get('/v1/research-alerts/status',headers=h).status_code==403
    data=preview().model_dump();data['alert']['organization_id']=OTHER;data['preferences'][0]['organization_id']=OTHER
    assert enabled.post('/v1/research-alerts/preview',headers=headers(),json=data).status_code==422


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_dangerous_activation_disables_preview(enabled,monkeypatch,flag):
    monkeypatch.setenv(flag,'1')
    assert enabled.get('/v1/research-alerts/status',headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_live_actions_remain_blocked_even_with_admin(enabled,action):
    assert enabled.post('/v1/research-alerts/'+action,headers=headers()).status_code==503


def test_invalid_request_does_not_echo_contacts(enabled):
    data=preview().model_dump();data['preferences'][0]['email']='private@example.org'
    response=enabled.post('/v1/research-alerts/preview',headers=headers(),json=data)
    assert response.status_code==422 and 'private@example.org' not in response.text
    data=preview().model_dump();data['alert']['publication_authorized']=True
    assert enabled.post('/v1/research-alerts/preview',headers=headers(),json=data).status_code==422


def test_pure_composition_has_no_network_or_persistence(monkeypatch):
    import socket
    import builtins
    from app import newsletter_alerts_v1130 as module
    def forbidden(*a,**k):raise AssertionError('Unexpected I/O')
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(builtins,'open',forbidden)
    assert compose(preview(),ORG)['preview_eligible_count']==1
    tree=ast.parse(Path(module.__file__).read_text())
    names={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
    names.update(a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names)
    assert not names.intersection({'smtplib','httpx','requests','sqlite3','sqlalchemy','subprocess'})
