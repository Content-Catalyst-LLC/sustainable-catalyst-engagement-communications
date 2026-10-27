from datetime import datetime, timezone, timedelta
from uuid import uuid4
import hashlib
import json
import pytest
from pydantic import ValidationError
from app.media_relations_v1140 import OutletClassification, PressPackage, assess, BLOCKED_ACTIONS
from app.offline_staging import seal, DISABLED
import time
from fastapi.testclient import TestClient
from app.main import app
from app.identity import mint_token
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001'
OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production'

@pytest.fixture
def enabled(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(organization=ORG,roles=('administrator',)):
    token=mint_token(subject='synthetic-press-review',organization_id=organization,roles=list(roles),expires_at=int(time.time())+300,secret=KEY)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':organization}

NOW=datetime(2026,10,27,tzinfo=timezone.utc)

def outlet(**changes):
    data=dict(synthetic=True,organization_id=ORG,outlet_ref='synthetic:'+str(uuid4()),kind='academic',topics=['methods'])
    data.update(changes);return OutletClassification(**data)


def package(**changes):
    data=dict(synthetic=True,organization_id=ORG,package_ref='press:example',revision='r1',headline='Synthetic research brief',
              pitch='Synthetic pitch for editorial review',source_refs=['source:example'],spokesperson_ref='synthetic:'+str(uuid4()),
              as_of=NOW,outlets=[outlet()],review_state='approved-preview',rights_reviewed=True,sources_verified=True,
              spokesperson_verified=True,institutional_approved=True,editorial_reviewed=True,privacy_reviewed=True)
    data.update(changes);return PressPackage(**data)


@pytest.fixture
def media(enabled,monkeypatch):
    monkeypatch.setenv('SCEC_MEDIA_STAGING_ENABLED','1');return enabled


def test_reviewed_press_is_still_offline():
    result=assess(package(),ORG)
    assert result['pitch_preview'] and len(result['eligible_synthetic_outlets'])==1
    assert all(result[k] is False for k in DISABLED)
    assert len(result['live_acceptance_gates_pending'])==7


@pytest.mark.parametrize('gate',['rights_reviewed','sources_verified','spokesperson_verified','institutional_approved','editorial_reviewed','privacy_reviewed'])
def test_each_review_blocks_pitch(gate):
    assert assess(package(**{gate:False}),ORG)['pitch_preview'] is None
    with pytest.raises(ValidationError):package(**{gate:'yes'})


@pytest.mark.parametrize('state',['draft','review','denied'])
def test_review_states_fail_closed(state):
    assert not assess(package(review_state=state),ORG)['eligible_synthetic_outlets']


def test_embargo_is_time_aware_and_reproducible():
    embargo=NOW+timedelta(days=1);p=package(embargo_until=embargo)
    assert assess(p,ORG)['embargo_active'] and assess(p,ORG)['pitch_preview'] is None
    data=p.model_dump();data['as_of']=embargo
    assert not assess(PressPackage(**data),ORG)['embargo_active']
    with pytest.raises(ValidationError):package(as_of=datetime(2026,10,27))
    with pytest.raises(ValidationError):package(embargo_until=datetime(2026,10,28))


def test_suppression_and_ordering():
    a=outlet();b=outlet(suppressed=True)
    p=package(outlets=[a,b]);q=p.model_dump();q['outlets'].reverse()
    assert assess(p,ORG)==assess(PressPackage(**q),ORG)
    assert assess(p,ORG)['eligible_synthetic_outlets']==[a.outlet_ref]
    assert not assess(package(suppressed=True),ORG)['eligible_synthetic_outlets']


@pytest.mark.parametrize('field',['email','phone','contact_name','recipient_export','mailing_list'])
def test_no_actual_contact_fields(field):
    with pytest.raises(ValidationError):outlet(**{field:'private@example.org'})


@pytest.mark.parametrize('changes',[{'headline':'<script>bad</script>'},{'pitch':'private@example.org'},{'source_refs':[]},{'outlets':[]},{'revision':'r'*49}])
def test_malformed_press_fields(changes):
    with pytest.raises(ValidationError):package(**changes)


def test_duplicate_and_cross_tenant_identifiers():
    a=outlet()
    with pytest.raises(ValidationError):package(outlets=[a,a])
    with pytest.raises(ValidationError):package(outlets=[outlet(organization_id=OTHER)])
    with pytest.raises(ValueError):assess(package(),OTHER)
    with pytest.raises(ValidationError):package(spokesperson_ref='real-person@example.org')


def test_hash_covers_revision_sources_and_reviews():
    p=package();initial=assess(p,ORG)['sha256']
    for change in [{'revision':'r2'},{'source_refs':['source:other']},{'privacy_reviewed':False}]:
        data=p.model_dump();data.update(change)
        assert initial!=assess(PressPackage(**data),ORG)['sha256']


def test_shared_envelope_cannot_spoof_authority():
    x=seal({'release':'fake','organization_id':OTHER,'production_certified':True},ORG,'11.4.0')
    assert x['release']=='11.4.0' and x['organization_id']==ORG and x['production_certified'] is False
    digest=x.pop('sha256')
    assert hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()==digest


def test_default_off(media,monkeypatch):
    monkeypatch.setenv('SCEC_MEDIA_STAGING_ENABLED','0')
    assert media.get('/v1/media-relations/status',headers=headers()).status_code==503


def test_service_privilege_and_tenant(media):
    assert media.get('/v1/media-relations/status',headers=headers()).status_code==200
    assert media.get('/v1/media-relations/status').status_code==401
    assert media.get('/v1/media-relations/status',headers=headers(roles=('viewer',))).status_code==403
    assert media.get('/v1/media-relations/status',headers=headers(organization=OTHER)).status_code==403
    p=package(organization_id=OTHER,outlets=[outlet(organization_id=OTHER)])
    assert media.post('/v1/media-relations/preview',headers=headers(),json=p.model_dump(mode='json')).status_code==422


def test_http_preview_and_private_validation(media):
    data=package().model_dump(mode='json')
    assert media.post('/v1/media-relations/preview',headers=headers(),json=data).status_code==200
    data['outlets'][0]['email']='private@example.org'
    response=media.post('/v1/media-relations/preview',headers=headers(),json=data)
    assert response.status_code==422 and 'private@example.org' not in response.text


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_admin_cannot_transmit(media,action):
    assert media.post('/v1/media-relations/'+action,headers=headers()).status_code==503


def test_dangerous_flags_deny(media,monkeypatch):
    for flag in ['SCEC_OUTBOUND_ENABLED','SCEC_PUBLICATION_ENABLED','SCEC_FEDERATION_ENABLED']:
        with monkeypatch.context() as patch:
            patch.setenv(flag,'1')
            assert media.get('/v1/media-relations/status',headers=headers()).status_code==503
