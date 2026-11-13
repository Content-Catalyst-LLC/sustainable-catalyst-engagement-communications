"""Run only against the dedicated synthetic Media acceptance database, never production."""
import json
import os
from pathlib import Path
import subprocess
import time
import secrets
import httpx
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import app
from app.identity import mint_token
from app import media09_press as press, media09_web as web
from app.persistence.models import TABLES
from app.persistence.media09 import press_inquiry_details
from app.persistence.audit import audit_events

url=os.environ['SCEC_DATABASE_URL']
assert url.split('?')[0].endswith('/scec_engagement_media09_acceptance')
assert os.environ.get('SCEC_ENV')=='development'
org,other=uuid4(),uuid4()
os.environ['SCEC_ALLOWED_ORGANIZATION_IDS']=f'{org},{other}'
os.environ['SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID']=str(org)
client=TestClient(app)

def headers(tenant,role='administrator'):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-operator',organization_id=tenant,
        roles={role},expires_at=int(time.time())+600,secret=os.environ['SCEC_IDENTITY_SIGNING_KEY']),
        'X-SCEC-Organization-ID':str(tenant)}

def payload(**values):
    return dict(synthetic=True,idempotency_key=str(uuid4()),name='Synthetic Press Person',email='press@example.org',
        subject='Synthetic public methods inquiry',message='Please share the public methods summary for review.',kind='press',
        privacy_notice_version=press.NOTICE,consent_to_reply=True,company='')|values

checks={}
for n,tenant in enumerate((org,other)):
    r=client.post('/v1/engagement/organizations',headers=headers(tenant),json={'id':str(tenant),'name':f'Synthetic Institution {n}','slug':f'synthetic-{n}'})
    assert r.status_code==201,r.text
engine=create_engine(url)
def create(p,tenant=org):
    with Session(engine) as db:return press.create_record(db,tenant,press.PressInquiryCreate(**p))
p=payload()
with ThreadPoolExecutor(max_workers=4) as pool: results=list(pool.map(lambda _:create(p),range(4)))
assert sum(r['created'] for r in results)==1
ident=results[0]['inquiry_id'];checks['concurrent_replay_one_inquiry']=True
try:create(p|{'subject':'Changed synthetic subject'})
except HTTPException as e:assert e.status_code==409
else:raise AssertionError('Expected idempotency conflict')
checks['modified_replay_conflict']=True
create(payload())
with engine.connect() as db:
    assert db.execute(select(func.count()).select_from(TABLES['contacts']).where(TABLES['contacts'].c.organization_id==org)).scalar_one()==1
    assert db.execute(select(func.count()).select_from(audit_events).where(audit_events.c.organization_id==org)).scalar_one()==6 # org + contact + 2 inquiry + 2 details
checks['canonical_contact_deduplicated']=True
checks['atomic_records_and_audit']=True
base='/v1/media09/press/inquiries/'+ident
r=client.get(base,headers=headers(org));assert r.status_code==200 and r.json()['email']=='press@example.org'
assert client.get(base,headers=headers(other)).status_code==404
assert client.get(base).status_code==401
assert client.get(base,headers=headers(org,'viewer')).status_code==403
forged=headers(org);forged['X-SCEC-Organization-ID']=str(other)
assert client.get(base,headers=forged).status_code==403
checks['tenant_role_anonymous_denial']=True
assert client.patch(base+'/status',headers=headers(org,'contact_editor'),json={'status':'closed','expected_version':1}).status_code==403
assert client.patch(base+'/status',headers=headers(org),json={'status':'reviewing','expected_version':1}).status_code==200
assert client.patch(base+'/status',headers=headers(org),json={'status':'closed','expected_version':1}).status_code==409
# Assignment through the same database and staff service, using a provisioned synthetic subject.
os.environ['SCEC_HUMAN_MEMBERSHIPS']=json.dumps({'synthetic-operator':{'organization_id':str(org),'roles':['administrator']}})
# Exercise optional export with the real persistence path and a mock provider.
from app.hubspot import HubSpot
calls=[]
def provider(request):
    calls.append(request)
    if request.url.path.endswith('/search'):return httpx.Response(200,json={'results':[]})
    assert set(json.loads(request.content)['properties'])=={'email','firstname'}
    return httpx.Response(201,json={'id':'123'})
class MockHubSpot(HubSpot):
    def __init__(self,token):super().__init__(token,transport=httpx.MockTransport(provider))
credential=Path(os.environ['MEDIA09_RECEIPT']).parent/'mock-hubspot-token'
credential.write_text('synthetic-only-not-a-provider-credential');credential.chmod(0o600)
os.environ['SCEC_HUBSPOT_TOKEN_FILE']=str(credential)
os.environ['SCEC_MEDIA09_HUBSPOT_ENABLED']='1'
original_connector=web.HubSpot;web.HubSpot=MockHubSpot
try:
    with Session(engine) as db:
        outcome=web.sync_contact(__import__('uuid').UUID(ident),web.SyncApproval(expected_version=2,approved=True),(org,'synthetic-operator',{'administrator'}),db)
    assert outcome['state']=='synced' and outcome['provider_id']=='123' and len(calls)==2
finally:
    web.HubSpot=original_connector
    os.environ.pop('SCEC_MEDIA09_HUBSPOT_ENABLED')
checks['mock_contact_sync_outcome_persisted']=True
# Actual platform session-store, CSRF and logout paths; no OIDC provider claim.
from app import human_auth
origin='https://media09.example.test'
for k,v in {'SCEC_HUMAN_AUTH_ENABLED':'1','SCEC_HUMAN_AUTH_MEDIA09_STAGING_ENABLED':'1',
    'SCEC_HUMAN_AUTH_ORIGIN':origin,'SCEC_HUMAN_SESSION_DB':str(Path(os.environ['MEDIA09_RECEIPT']).parent/'fixture-sessions.sqlite3'),
    'SCEC_OIDC_ISSUER':'https://idp.example.test','SCEC_OIDC_CLIENT_ID':'synthetic-media09',
    'SCEC_OIDC_CLIENT_SECRET':'synthetic-fixture-not-a-real-secret','SCEC_OIDC_AUTH_URL':'https://idp.example.test/auth',
    'SCEC_OIDC_TOKEN_URL':'https://idp.example.test/token','SCEC_OIDC_JWKS_URL':'https://idp.example.test/keys',
    'SCEC_OIDC_REDIRECT_URI':origin+'/v1/human-auth/callback','SCEC_MEDIA09_ORIGIN':origin}.items():os.environ[k]=v
cookie=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(48)
with human_auth.store(human_auth.config()) as store:
    store.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',(human_auth.digest(cookie),'synthetic-operator',str(org),json.dumps(['administrator']),human_auth.digest(csrf),int(time.time())+120))
    store.commit()
browser=TestClient(app,base_url=origin)
browser.cookies.set(human_auth.SESSION_COOKIE,cookie)
assert browser.get('/press/inbox').status_code==200
assert browser.get('/press/staff/inquiries').status_code==200
assert browser.patch('/press/staff/inquiries/'+ident+'/assignment',json={'subject':'synthetic-operator','expected_version':3}).status_code==403
r=browser.patch('/press/staff/inquiries/'+ident+'/assignment',headers={'origin':origin,'x-scec-csrf':csrf},json={'subject':'synthetic-operator','expected_version':3})
assert r.status_code==200 and r.json()['version']==4,r.text
assert browser.post('/v1/human-auth/logout',headers={'origin':origin,'x-scec-csrf':csrf}).status_code==204
assert browser.get('/press/inbox',follow_redirects=False).status_code==303
checks['fixture_session_inbox_csrf_logout']=True
assert client.patch(base+'/status',headers=headers(org),json={'status':'closed','expected_version':4}).status_code==200
assert client.patch(base+'/status',headers=headers(org),json={'status':'reviewing','expected_version':5}).status_code==409
checks['review_assignment_close_cas']=True
for _ in range(3):create(payload())
try:create(payload())
except HTTPException as e:assert e.status_code==429
else:raise AssertionError('Expected rate limit')
checks['five_per_minute']=True
# New connection/app client proves records survive disposal of application pools.
engine.dispose()
assert TestClient(app).get(base,headers=headers(org)).json()['status']=='closed'
checks['reconnected_persistence']=True
# Force a post-inquiry write error and prove all canonical inserts rolled back.
failing=payload();bad_org=uuid4()
try:create(failing,bad_org)
except HTTPException as e:assert e.status_code==422
else:raise AssertionError('Unknown organization accepted')
with engine.connect() as db:
    assert db.execute(select(TABLES['inquiries'].c.id).where(TABLES['inquiries'].c.id==press._id(bad_org,__import__('uuid').UUID(failing['idempotency_key'])))).first() is None
# Prove rollback after canonical writes, with a temporary constraint in this
# dedicated fixture database. The second tenant has no rate-cap consumption.
forced=payload(email='rollback@example.org',message='Synthetic forced rollback case.')
with engine.begin() as db:
    db.execute(text("ALTER TABLE media09_press_inquiries ADD CONSTRAINT fixture_rollback CHECK (body <> 'Synthetic forced rollback case.')"))
try:
    try:create(forced,other)
    except HTTPException as e:assert e.status_code==409
    else:raise AssertionError('Expected forced transactional failure')
    with engine.connect() as db:
        assert db.execute(select(func.count()).select_from(TABLES['contacts']).where(TABLES['contacts'].c.organization_id==other)).scalar_one()==0
        assert db.execute(select(func.count()).select_from(TABLES['inquiries']).where(TABLES['inquiries'].c.organization_id==other)).scalar_one()==0
finally:
    with engine.begin() as db:db.execute(text('ALTER TABLE media09_press_inquiries DROP CONSTRAINT fixture_rollback'))
checks['failed_write_no_partial_inquiry']=True
for route in ('send','crm-export','public-submit'):
    assert client.post('/v1/media09/press/'+route,headers=headers(org),json=payload()).status_code==503
checks['no_sending_export']=True
report={'result':'PASS_SYNTHETIC_POSTGRES','checks':checks,'tenant':str(org),'source_sha':os.environ['MEDIA09_SOURCE_SHA']}
Path(os.environ['MEDIA09_RECEIPT']).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'result':report['result'],'checks':checks}))
