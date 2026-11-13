import time
from uuid import uuid4
from fastapi.testclient import TestClient
import pytest
from app.main import app
from app import media09_press as press, media09_web as web, human_auth

client=TestClient(app,base_url='https://press.example.test')

@pytest.fixture
def setup(monkeypatch):
    org=uuid4()
    values={'SCEC_MEDIA09_PRESS_STAGING_ENABLED':'1','SCEC_MEDIA09_WEB_STAGING_ENABLED':'1',
        'SCEC_ENV':'development','SCEC_PERSISTENCE_ENABLED':'1','SCEC_ALLOWED_ORGANIZATION_IDS':str(org),
        'SCEC_DATABASE_URL':'postgresql+psycopg://fixture:fixture@127.0.0.1/scec_engagement_test',
        'SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID':str(org),'SCEC_MEDIA09_ORIGIN':'https://press.example.test',
        'SCEC_IDENTITY_SIGNING_KEY':'synthetic-form-signing-key-1234567890'}
    for k,v in values.items():monkeypatch.setenv(k,v)
    app.dependency_overrides[web.session]=lambda:object()
    client.cookies.clear()
    yield org
    app.dependency_overrides.clear()

def payload():
    return {'synthetic':True,'idempotency_key':str(uuid4()),'name':'Synthetic Person',
        'email':'press@example.org','subject':'Public evidence inquiry','message':'Synthetic request for public methods.',
        'kind':'press','privacy_notice_version':press.NOTICE,'consent_to_reply':True,'company':''}

def token():
    r=client.get('/press/');assert r.status_code==200
    assert 'frame-ancestors' in r.headers['content-security-policy']
    assert 'HttpOnly' in r.headers['set-cookie'] and 'Secure' in r.headers['set-cookie']
    return client.cookies.get(web.COOKIE)

def test_form_no_credentials_and_synthetic_notice(setup):
    r=client.get('/press/');assert r.status_code==200
    assert 'Do not enter real personal information' in r.text
    assert 'Bearer' not in r.text
    assert r.headers['cache-control']=='no-store'
    assert client.get('/press/assets/press.js').status_code==200
    assert client.get('/press/assets/secrets').status_code==404

def test_submit_receipt_and_csrf(setup,monkeypatch):
    value=token()
    monkeypatch.setattr(press,'create_record',lambda *args:press._receipt(uuid4(),'new',1,True))
    headers={'origin':'https://press.example.test','x-sc-form':value}
    r=client.post('/press/inquiries',headers=headers,json=payload());assert r.status_code==201,r.text
    assert 'press@example.org' not in r.text
    assert client.post('/press/inquiries',headers={'origin':'https://evil.test','x-sc-form':value},json=payload()).status_code==403
    assert client.post('/press/inquiries',headers={'origin':'https://press.example.test'},json=payload()).status_code==403

def test_real_data_and_oversize_denied(setup):
    headers={'origin':'https://press.example.test','x-sc-form':token()}
    data=payload();data['email']='private@gmail.com'
    r=client.post('/press/inquiries',headers=headers,json=data)
    assert r.status_code==422 and 'private@gmail.com' not in r.text
    assert client.post('/press/inquiries',headers=headers,content=b'x'*9000).status_code==413

def test_production_and_default_off(setup,monkeypatch):
    monkeypatch.setenv('SCEC_ENV','production')
    assert client.get('/press/').status_code==503
    monkeypatch.setenv('SCEC_ENV','development');monkeypatch.delenv('SCEC_MEDIA09_WEB_STAGING_ENABLED')
    assert client.get('/press/').status_code==503

def test_staff_no_service_token_browser_bypass(setup,monkeypatch):
    monkeypatch.setattr(human_auth,'config',lambda:{})
    assert client.get('/press/inbox').status_code==401
    assert client.get('/press/staff/inquiries',headers={'authorization':'Bearer synthetic'}).status_code==401

def test_staff_rechecks_membership_and_csrf(setup,monkeypatch):
    org=setup
    monkeypatch.setattr(human_auth,'config',lambda:{})
    monkeypatch.setattr(human_auth,'current_session',lambda *a:{'subject':'reviewer','organization_id':str(org),'csrf_hash':human_auth.digest('x'*32)})
    monkeypatch.setattr(human_auth,'resolve_member',lambda s:(str(org),['contact_editor']))
    assert client.get('/press/inbox').status_code==200
    url='/press/staff/inquiries/'+str(uuid4())+'/status'
    assert client.patch(url,json={'status':'reviewing','expected_version':1}).status_code==403
    headers={'origin':'https://press.example.test','x-scec-csrf':'x'*32}
    assert client.patch(url,headers=headers,json={'status':'closed','expected_version':1}).status_code==403
    monkeypatch.setattr(human_auth,'resolve_member',lambda s:(str(org),['viewer']))
    assert client.get('/press/inbox').status_code==403
    monkeypatch.setattr(human_auth,'resolve_member',lambda s:(str(uuid4()),['administrator']))
    assert client.get('/press/inbox').status_code==403

def test_assignment_target_and_disconnected_crm(setup,monkeypatch):
    org=setup
    app.dependency_overrides[web.staff]=lambda:(org,'staff',{'administrator'})
    monkeypatch.setattr(human_auth,'resolve_member',lambda s:(str(uuid4()),['administrator']))
    ident=uuid4()
    assert client.patch(f'/press/staff/inquiries/{ident}/assignment',json={'subject':'other','expected_version':1}).status_code==403
    monkeypatch.delenv('SCEC_MEDIA09_HUBSPOT_ENABLED',raising=False)
    assert client.post(f'/press/staff/inquiries/{ident}/hubspot',json={'approved':True,'expected_version':1}).status_code==503

def test_real_intake_requires_owner_records(setup,monkeypatch,tmp_path):
    import json
    monkeypatch.setenv('SCEC_ENV','production')
    monkeypatch.setenv('SCEC_MEDIA09_REAL_INTAKE_ENABLED','1')
    assert client.get('/press/').status_code==503
    notice=tmp_path/'approved-test-notice.json'
    values={'version':'TEST-APPROVAL-NOT-A-REAL-RELEASE','text':'Fixture notice <not markup>',
        'privacy_url':'https://example.org/privacy','privacy_approval_ref':'test-only',
        'security_approval_ref':'test-only','identity_acceptance_ref':'test-only','cutover_authorization_ref':'test-only'}
    notice.write_text(json.dumps(values));notice.chmod(0o600)
    monkeypatch.setenv('SCEC_MEDIA09_APPROVED_NOTICE_FILE',str(notice))
    response=client.get('/press/')
    assert response.status_code==200 and 'data-mode="real"' in response.text
    assert '&lt;not markup&gt;' in response.text and '<not markup>' not in response.text
    assert 'Do not enter real personal information' not in response.text
    data=payload()|{'synthetic':False,'name':'Fixture Institution Desk','privacy_notice_version':values['version']}
    seen=[]
    monkeypatch.setattr(press,'create_record',lambda db,org,p:(seen.append(p) or press._receipt(uuid4(),'new',1,True,p.synthetic)))
    headers={'origin':'https://press.example.test','x-sc-form':client.cookies.get(web.COOKIE)}
    result=client.post('/press/inquiries',headers=headers,json=data)
    assert result.status_code==201 and result.json()['synthetic_only'] is False
    assert isinstance(seen[0],press.RealPressInquiryCreate)
    data['privacy_notice_version']='OLD'
    assert client.post('/press/inquiries',headers=headers,json=data).status_code==422
    for key in ('privacy_approval_ref','security_approval_ref','identity_acceptance_ref','cutover_authorization_ref'):
        notice.write_text(json.dumps({k:v for k,v in values.items() if k!=key}))
        assert client.get('/press/').status_code==503
    notice.write_text(json.dumps(values));notice.chmod(0o644)
    assert client.get('/press/').status_code==503
