"""Real PostgreSQL only in the named, synthetic acceptance DB; skipped elsewhere."""
import json,os,secrets,subprocess
from pathlib import Path
from datetime import datetime,timedelta,timezone
from uuid import uuid4,UUID
import pytest
from sqlalchemy import create_engine,insert,select,update,delete,func,text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import media09_privacy as p,media09_rights as r,media09_press as press,media09_web as web,human_auth
from app.persistence.models import TABLES
from app.persistence.media09_privacy import rights_requests,legal_holds,attachments,deletion_receipts,privacy_state
from app.persistence.audit import audit_events
from app.contracts.canonical import Organization
from app.contact_service import put_record,read_record
from app.main import app

URL=os.getenv('MEDIA09_PRIVACY_TEST_DATABASE_URL','')
pytestmark=pytest.mark.skipif(not URL,reason='Explicit isolated PostgreSQL acceptance URL required')

@pytest.fixture
def fixture(monkeypatch,tmp_path):
    assert make_url(URL).database=='scec_engagement_media09_acceptance'
    root=tmp_path/'privacy';root.mkdir(mode=0o700)
    secret=root/'key';secret.write_text(secrets.token_hex(32));secret.chmod(0o600)
    for name in ('attachments','backups'):(root/name).mkdir(mode=0o700)
    org,other=uuid4(),uuid4()
    values={'SCEC_MEDIA09_PRIVACY_ENABLED':'1','SCEC_MEDIA09_PRIVACY_KEY_FILE':str(secret),
        'SCEC_MEDIA09_SUPPRESSION_FILE':str(root/'suppression.json'),'SCEC_MEDIA09_NEW_SYNTHETIC_BASELINE':'1',
        'SCEC_MEDIA09_ATTACHMENT_ROOT':str(root/'attachments'),'SCEC_MEDIA09_BACKUP_ROOT':str(root/'backups'),
        'SCEC_DATABASE_URL':URL,'SCEC_PERSISTENCE_ENABLED':'1','SCEC_ENV':'development',
        'SCEC_ALLOWED_ORGANIZATION_IDS':f'{org},{other}','SCEC_IDENTITY_MODE':'bound',
        'SCEC_IDENTITY_SIGNING_KEY':'synthetic-test-signing-key-never-production-123456789',
        'SCEC_MEDIA09_WEB_STAGING_ENABLED':'1','SCEC_MEDIA09_PRESS_STAGING_ENABLED':'1',
        'SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID':str(org),'SCEC_MEDIA09_ORIGIN':'https://media09.example.test'}
    for k,v in values.items():monkeypatch.setenv(k,v)
    for k in ('SCEC_MEDIA09_REAL_INTAKE_ENABLED','SCEC_MEDIA09_REAL_ERASURE_ENABLED','SCEC_MEDIA09_HUBSPOT_ENABLED','SCEC_MEDIA09_RETENTION_POLICY_FILE'):monkeypatch.delenv(k,raising=False)
    p.initialize_ledger();monkeypatch.delenv('SCEC_MEDIA09_NEW_SYNTHETIC_BASELINE')
    engine=create_engine(URL)
    for o in (org,other):
        with Session(engine) as db:put_record('organizations',{'id':str(o),'name':'Synthetic Institution','slug':'synthetic-'+o.hex},o,db)
    yield engine,org,other,root,monkeypatch
    app.dependency_overrides.clear();engine.dispose()


def payload(**values):
    return dict(synthetic=True,idempotency_key=uuid4(),name='Synthetic Press Person',email='press@example.org',
        subject='Synthetic methods inquiry',message='Please share the public research methods summary.',kind='press',
        privacy_notice_version=press.NOTICE,privacy_notice_acknowledged=True)|values


def inquiry(f,**values):
    engine,org,*_=f
    with Session(engine) as db:receipt=press.create_record(db,org,press.PressInquiryCreate(**payload(**values)))
    with engine.connect() as db:row=db.execute(select(p.details).where(p.details.c.id==UUID(receipt['inquiry_id']))).mappings().one()
    return dict(row)


def policy(f,**values):
    root,mp=f[3:];path=root/'policy.json'
    path.write_text(p.RetentionPolicy(**values).model_dump_json());path.chmod(0o600)
    mp.setenv('SCEC_MEDIA09_RETENTION_POLICY_FILE',str(path))


def request(f,cid,kind='erase'):
    engine,org,*_=f
    with Session(engine) as db,db.begin():receipt=r.create(db,org,r.RightsCreate(email='press@example.org',kind=kind,privacy_notice_acknowledged=True))
    ident=UUID(receipt['request_id'])
    with Session(engine) as db,db.begin():r.review(db,org,ident,r.RightsReview(expected_version=1,action='verify',contact_id=cid,evidence_ref='fixture_evidence'))
    return ident


def test_full_erasure_owned_attachment_and_receipt(fixture):
    f=fixture;engine,org,other,root,_=f;row=inquiry(f);rid=request(f,row['contact_id'])
    aid=uuid4();key=f'{org}/{row["id"]}/{aid}';path=root/'attachments'/key;path.parent.mkdir(parents=True);path.write_bytes(b'synthetic file')
    with Session(engine) as db,db.begin():db.execute(insert(attachments).values(id=aid,organization_id=org,inquiry_id=row['id'],object_key=key,created_at=p.now()))
    with Session(engine) as db,db.begin():
        result=r.review(db,org,rid,r.RightsReview(expected_version=2,action='erase',evidence_ref='fixture_erasure'))
    assert result['erasure_receipt'] and not path.exists()
    with engine.connect() as db:
        for table in (TABLES['contacts'],TABLES['inquiries'],p.details,attachments):assert db.execute(select(func.count()).select_from(table).where(table.c.organization_id==org)).scalar_one()==0
        assert db.execute(select(func.count()).select_from(audit_events).where(audit_events.c.organization_id==org,audit_events.c.record_id.in_([row['id'],row['contact_id']]))).scalar_one()==0
        rights=db.execute(select(rights_requests).where(rights_requests.c.id==rid)).mappings().one()
        assert rights['requester_email'] is None and rights['contact_id'] is None and rights['verification_ref'] is None
        receipt=db.execute(select(deletion_receipts).where(deletion_receipts.c.id==UUID(result['erasure_receipt']))).mappings().one()
        serialized=json.dumps(dict(receipt),default=str)
        assert str(row['id']) not in serialized and str(row['contact_id']) not in serialized and 'press@example.org' not in serialized
    ledger=(root/'suppression.json').read_text()
    assert str(row['id']) not in ledger and str(row['contact_id']) not in ledger and 'press@example.org' not in ledger
    with Session(engine) as db:
        with pytest.raises(HTTPException) as exc:read_record('contacts',row['contact_id'],org,db)
        assert exc.value.status_code==410
    # A new voluntary inquiry is allowed, while replaying an erased identifier is not.
    newer=inquiry(f);assert newer['contact_id']!=row['contact_id']


def test_hold_blocks_retention_erasure_and_backup(fixture):
    f=fixture;engine,org,_,root,_=f;row=inquiry(f);rid=request(f,row['contact_id']);policy(f,enabled=True)
    with Session(engine) as db,db.begin():
        h=r.hold(db,org,r.HoldCreate(contact_id=row['contact_id'],reason='litigation',case_ref='fixture_case',review_at=p.now()+timedelta(days=1)))
        db.execute(update(p.details).where(p.details.c.id==row['id']).values(last_substantive_at=p.months(p.now(),-14),status='closed'))
    with Session(engine) as db,db.begin():
        out=p.run_retention(db,org);assert out['held_count']==1 and out['receipts']==[]
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException) as exc:r.review(db,org,rid,r.RightsReview(expected_version=2,action='erase',evidence_ref='fixture_erasure'))
        assert exc.value.status_code==423
    bid=uuid4();path=root/'backups'/f'{bid}.dump';path.write_bytes(b'synthetic-backup')
    with Session(engine) as db,db.begin():p.register_backup(db,org,bid,synthetic_only=True,created_at=p.now()-timedelta(days=100))
    with Session(engine) as db,db.begin():assert p.expire_backups(db,org)['held'] is True
    assert path.exists()
    # Overdue is not an automatic release.
    with Session(engine) as db,db.begin():db.execute(update(legal_holds).where(legal_holds.c.id==UUID(h['hold_id'])).values(review_at=p.now()-timedelta(days=1)))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException):p.erase(db,org,row['contact_id'])
    with Session(engine) as db,db.begin():r.release_hold(db,org,UUID(h['hold_id']),1,'fixture_release')
    with Session(engine) as db,db.begin():assert p.expire_backups(db,org)['expired']==1
    assert not path.exists()
    with pytest.raises(HTTPException) as exc:p.assert_backup_restorable(bid)
    assert exc.value.status_code==410
    with Session(engine) as db,db.begin():assert len(p.run_retention(db,org)['receipts'])==1


def test_retention_calendar_boundaries_review_and_no_real_activation(fixture):
    f=fixture;engine,org,*_=f;row=inquiry(f)
    at=datetime(2026,11,13,12,tzinfo=timezone.utc)
    with Session(engine) as db,db.begin():db.execute(update(p.details).where(p.details.c.id==row['id']).values(status='closed',last_substantive_at=datetime(2025,11,13,12,tzinfo=timezone.utc)))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException) as exc:p.run_retention(db,org,at=at)
        assert exc.value.status_code==503
    with Session(engine) as db:
        assert p.retention_preview(db,org,at-timedelta(seconds=1))['items']==[]
        assert p.retention_preview(db,org,at)['items'][0]['action']=='erase'
    policy(f,enabled=True)
    with Session(engine) as db,db.begin():assert len(p.run_retention(db,org,at=at)['receipts'])==1
    active=inquiry(f,email='active@example.org')
    with Session(engine) as db,db.begin():db.execute(update(p.details).where(p.details.c.id==active['id']).values(last_substantive_at=p.months(at,-7)))
    with Session(engine) as db:
        assert p.retention_preview(db,org,at)['items'][0]['action']=='review'
    with Session(engine) as db,db.begin():
        db.execute(update(p.details).where(p.details.c.id==active['id']).values(synthetic_only=False,reply_consent=False,status='closed',last_substantive_at=p.months(at,-13)))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException) as exc:p.run_retention(db,org,at=at)
        assert exc.value.status_code==503


def test_rights_verify_restrict_rectify_access_response_and_deadlines(fixture):
    f=fixture;engine,org,*_=f;row=inquiry(f)
    with Session(engine) as db,db.begin():
        q=r.create(db,org,r.RightsCreate(email='press@example.org',kind='access',privacy_notice_acknowledged=True));rid=UUID(q['request_id'])
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException):r.review(db,org,rid,r.RightsReview(expected_version=1,action='restrict',evidence_ref='fixture_evidence'))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException):r.review(db,org,rid,r.RightsReview(expected_version=1,action='verify',contact_id=uuid4(),evidence_ref='fixture_evidence'))
    with Session(engine) as db,db.begin():r.review(db,org,rid,r.RightsReview(expected_version=1,action='verify',contact_id=row['contact_id'],evidence_ref='fixture_evidence'))
    with Session(engine) as db:
        out=r.subject_data(db,org,rid);assert out['contact']['email']=='press@example.org' and len(out['inquiries'])==1
    with Session(engine) as db,db.begin():r.review(db,org,rid,r.RightsReview(expected_version=2,action='restrict',evidence_ref='fixture_restrict'))
    with Session(engine) as db:
        with pytest.raises(HTTPException) as exc:press.detail_record(db,org,row['id'])
        assert exc.value.status_code==423
        assert press.list_records(db,org,50,0)['items']==[]
    with Session(engine) as db,db.begin():r.review(db,org,rid,r.RightsReview(expected_version=3,action='release_restriction',evidence_ref='fixture_release'))
    with Session(engine) as db,db.begin():r.review(db,org,rid,r.RightsReview(expected_version=4,action='extend',evidence_ref='fixture_extension'))
    with Session(engine) as db:
        q=db.execute(select(rights_requests).where(rights_requests.c.id==rid)).mappings().one();assert q['due_at']==p.months(q['received_at'],3)
    with Session(engine) as db,db.begin():r.review(db,org,rid,r.RightsReview(expected_version=5,action='respond',evidence_ref='fixture_review',response_ref='fixture_response'))
    with Session(engine) as db,db.begin():r.review(db,org,rid,r.RightsReview(expected_version=6,action='close',evidence_ref='fixture_close'))
    rid2=request(f,row['contact_id'],'rectify')
    with Session(engine) as db,db.begin():r.correct(db,org,rid2,r.Correction(expected_version=2,display_name='Synthetic Corrected',email='corrected@example.org',evidence_ref='fixture_correction'))
    with Session(engine) as db:assert read_record('contacts',row['contact_id'],org,db)['email']=='corrected@example.org'


def test_failure_recovery_suppression_and_shared_record_guard(fixture):
    f=fixture;engine,org,_,root,_=f;row=inquiry(f)
    with Session(engine) as db,db.begin():
        contact=db.execute(select(TABLES['contacts'].c.payload).where(TABLES['contacts'].c.id==row['contact_id'])).scalar_one()
        db.execute(update(TABLES['contacts']).where(TABLES['contacts'].c.id==row['contact_id']).values(payload=dict(contact,marketing_consent=True)))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException) as exc:p.erase(db,org,row['contact_id'])
        assert exc.value.status_code==409
    with Session(engine) as db,db.begin():
        db.execute(update(TABLES['contacts']).where(TABLES['contacts'].c.id==row['contact_id']).values(payload=dict(contact,marketing_consent=False)))
    with Session(engine) as db,db.begin():
        # Scoped erasure may not silently delete a shared support-domain record.
        from app.contracts.canonical import Case
        case=Case(organization_id=org,title='Synthetic support',requester_contact_id=row['contact_id'])
        db.execute(insert(TABLES['cases']).values(id=case.id,organization_id=org,schema_version=case.schema_version,classification='restricted',created_at=p.now(),updated_at=p.now(),payload=case.model_dump(mode='json')))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException) as exc:p.erase(db,org,row['contact_id'])
        assert exc.value.status_code==409
    with Session(engine) as db,db.begin():db.execute(delete(TABLES['cases']).where(TABLES['cases'].c.id==case.id))
    try:
        with Session(engine) as db,db.begin():
            p.erase(db,org,row['contact_id']);raise RuntimeError('simulate transaction failure after durable suppression')
    except RuntimeError:pass
    with Session(engine) as db:
        with pytest.raises(HTTPException) as exc:p.guard(db,org)
        assert exc.value.status_code==503
    with Session(engine) as db,db.begin():p.apply_suppression(db,org)
    with Session(engine) as db:
        p.guard(db,org)
        assert db.execute(select(TABLES['contacts'].c.id).where(TABLES['contacts'].c.id==row['contact_id'])).first() is None


def test_actual_backup_restore_erasure_suppression(fixture):
    f=fixture;engine,org,_,root,_=f;row=inquiry(f);u=make_url(URL)
    env=os.environ|{'PGHOST':u.host,'PGPORT':str(u.port or 5432),'PGUSER':u.username,'PGPASSWORD':u.password or '', 'PGDATABASE':u.database}
    bid=uuid4();path=root/'backups'/f'{bid}.dump'
    path.touch(mode=0o600)
    with path.open('wb') as output:subprocess.run(['pg_dump','-Fc','--no-owner','--no-acl'],env=env,stdout=output,stderr=subprocess.PIPE,check=True)
    policy(f,enabled=True)
    with Session(engine) as db,db.begin():p.register_backup(db,org,bid,synthetic_only=True)
    with Session(engine) as db,db.begin():p.erase(db,org,row['contact_id'])
    p.assert_backup_restorable(bid)
    restore='scec_engagement_media09_privacy_restore_'+uuid4().hex[:10]
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:connection.execute(text('CREATE DATABASE '+restore))
    restored=create_engine(u.set(database=restore));restored_env=env|{'PGDATABASE':restore}
    try:
        subprocess.run(['pg_restore','--exit-on-error','--no-owner','--no-acl','-d',restore,str(path)],env=restored_env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
        with Session(restored) as db:
            with pytest.raises(HTTPException) as exc:p.guard(db,org)
            assert exc.value.status_code==503
        with Session(restored) as db,db.begin():p.apply_suppression(db,org)
        with Session(restored) as db:
            p.guard(db,org)
            assert db.execute(select(TABLES['contacts'].c.id).where(TABLES['contacts'].c.id==row['contact_id'])).first() is None
            assert db.execute(select(p.details.c.id).where(p.details.c.id==row['id'])).first() is None
    finally:
        restored.dispose()
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:connection.execute(text('DROP DATABASE '+restore))


def test_api_tenant_roles_csrf_and_followup_clock(fixture):
    f=fixture;engine,org,other,root,mp=f;row=inquiry(f)
    origin='https://media09.example.test'
    for k,v in {'SCEC_HUMAN_AUTH_ENABLED':'1','SCEC_HUMAN_AUTH_MEDIA09_STAGING_ENABLED':'1','SCEC_HUMAN_AUTH_ORIGIN':origin,
        'SCEC_HUMAN_SESSION_DB':str(root/'sessions.db'),'SCEC_OIDC_ISSUER':'https://idp.example.test',
        'SCEC_OIDC_CLIENT_ID':'synthetic-fixture','SCEC_OIDC_CLIENT_SECRET':'not-a-real-credential',
        'SCEC_OIDC_AUTH_URL':'https://idp.example.test/auth','SCEC_OIDC_TOKEN_URL':'https://idp.example.test/token',
        'SCEC_OIDC_JWKS_URL':'https://idp.example.test/keys','SCEC_OIDC_REDIRECT_URI':origin+'/v1/human-auth/callback',
        'SCEC_HUMAN_MEMBERSHIPS':json.dumps({'reviewer':{'organization_id':str(org),'roles':['contact_editor']},'admin':{'organization_id':str(org),'roles':['administrator']},'other':{'organization_id':str(other),'roles':['administrator']}})}.items():mp.setenv(k,v)
    client=TestClient(app,base_url=origin,follow_redirects=False)
    page=client.get('/press/privacy/rights');assert page.status_code==200
    token=client.cookies.get(web.COOKIE)
    q=client.post('/press/privacy/requests',headers={'origin':origin,'x-sc-form':token},json={'email':'press@example.org','kind':'erase','privacy_notice_acknowledged':True,'synthetic':True})
    assert q.status_code==200 and 'press@example.org' not in q.text
    rid=q.json()['request_id']
    assert client.get('/press/staff/privacy/requests').status_code==401
    def login(subject,tenant,roles):
        token=secrets.token_urlsafe(48);csrf=secrets.token_urlsafe(48)
        with human_auth.store(human_auth.config()) as db:
            db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',(human_auth.digest(token),subject,str(tenant),json.dumps(roles),human_auth.digest(csrf),int(__import__('time').time())+300));db.commit()
        client.cookies.set(human_auth.SESSION_COOKIE,token)
        return {'origin':origin,'x-scec-csrf':csrf}
    headers=login('reviewer',org,['contact_editor']);assert client.get('/press/staff/privacy/requests').status_code==403
    # Follow-up notes/assignment must not reset the retention clock.
    out=client.patch(f'/press/staff/inquiries/{row["id"]}/follow-up',headers=headers,json={'expected_version':1,'note':'Synthetic next step','follow_up_at':(p.now()+timedelta(days=1)).isoformat()});assert out.status_code==200,out.text
    with engine.connect() as db:assert db.execute(select(p.details.c.last_substantive_at).where(p.details.c.id==row['id'])).scalar_one()==row['last_substantive_at']
    headers=login('other',other,['administrator']);assert client.patch(f'/press/staff/privacy/requests/{rid}',headers=headers,json={'expected_version':1,'action':'verify','contact_id':str(row['contact_id']),'evidence_ref':'fixture_evidence'}).status_code==404
    headers=login('admin',org,['administrator'])
    assert client.get('/press/privacy').status_code==200
    assert client.patch(f'/press/staff/privacy/requests/{rid}',json={'expected_version':1,'action':'verify','contact_id':str(row['contact_id']),'evidence_ref':'fixture_evidence'}).status_code==403
    assert client.patch(f'/press/staff/privacy/requests/{rid}',headers=headers,json={'expected_version':1,'action':'verify','contact_id':str(row['contact_id']),'evidence_ref':'fixture_evidence'}).status_code==200


def test_log_expiry_and_suppression_minimization(fixture):
    f=fixture;engine,org,_,root,mp=f;row=inquiry(f)
    logs=root/'logs';logs.mkdir(mode=0o700);mp.setenv('SCEC_MEDIA09_LOG_ROOT',str(logs))
    old=logs/'media09-20260101.log';old.write_text('Synthetic operation event')
    unrelated=logs/'other-service.log';unrelated.write_text('do not touch')
    stamp=(p.now()-timedelta(days=31)).timestamp();os.utime(old,(stamp,stamp))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException):p.expire_logs(db,org,synthetic_only=True)
    policy(f,enabled=True,approval_ref='synthetic-policy-fixture')
    with Session(engine) as db,db.begin():assert p.expire_logs(db,org,synthetic_only=True)['expired']==1
    assert unrelated.exists()
    with Session(engine) as db,db.begin():p.erase(db,org,row['contact_id'])
    future=p.now()+timedelta(days=91)
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException):p.compact_suppression(db,org,at=future)
    mp.setenv('SCEC_MEDIA09_BACKUP_COVERAGE_APPROVAL_REF','synthetic-inventory-only')
    with Session(engine) as db,db.begin():assert p.compact_suppression(db,org,at=future)['markers_removed']==1
    with Session(engine) as db,db.begin():db.execute(delete(privacy_state).where(privacy_state.c.organization_id==org))
    with Session(engine) as db,db.begin():
        with pytest.raises(HTTPException) as exc:p.apply_suppression(db,org)
        assert exc.value.status_code==503


def test_manual_company_sync_is_scoped_minimal_and_durable(fixture):
    import httpx
    from app.hubspot import HubSpot
    from app.persistence.media09_privacy import company_syncs
    from pydantic import ValidationError
    f=fixture;engine,org,_,root,mp=f
    secret=root/'fake-crm-token';secret.write_text('synthetic-not-an-account-credential');secret.chmod(0o600)
    mp.setenv('SCEC_HUBSPOT_TOKEN_FILE',str(secret));mp.setenv('SCEC_MEDIA09_HUBSPOT_ENABLED','1')
    assert web.hubspot_status((org,'fixture',{'administrator'}))['status']=='approval_required'
    mp.setenv('SCEC_MEDIA09_HUBSPOT_PRIVACY_APPROVAL_REF','synthetic-fixture-only')
    saved=[];calls=[]
    def mock(req):
        calls.append(req)
        if req.url.path.endswith('/search'):return httpx.Response(200,json={'results':saved})
        body=json.loads(req.content)
        assert body=={'properties':{'domain':'example.org','name':'Synthetic Institution'}}
        saved[:]=[{'id':'456'}]
        return httpx.Response(201,json={'id':'456'})
    class MockHubSpot(HubSpot):
        def __init__(self,token):super().__init__(token,transport=httpx.MockTransport(mock))
    mp.setattr(web,'HubSpot',MockHubSpot)
    with Session(engine) as db:
        with pytest.raises(HTTPException) as exc:web.sync_company(web.CompanySync(approved=True,domain='example.org'),(org,'fixture',{'contact_editor'}),db)
        assert exc.value.status_code==403
    with pytest.raises(ValidationError):web.CompanySync(approved=True,domain='example.org',private_research='forbidden')
    for _ in range(2):
        with Session(engine) as db:assert web.sync_company(web.CompanySync(approved=True,domain='example.org'),(org,'fixture',{'administrator'}),db)['provider_id']=='456'
    assert [c.method for c in calls]==['POST','POST','POST','PATCH']
    with engine.connect() as db:assert db.execute(select(company_syncs.c.outcome).where(company_syncs.c.organization_id==org)).scalar_one()['state']=='synced'


def test_spam_relationship_and_reviewed_exception_boundaries(fixture):
    f=fixture;engine,org,*_=f;at=p.now()
    spam=inquiry(f,email='spam@example.org');relationship=inquiry(f,email='institution@example.org')
    with Session(engine) as db,db.begin():
        db.execute(update(p.details).where(p.details.c.id==spam['id']).values(disposition='spam',last_substantive_at=at-timedelta(days=30)))
        db.execute(update(p.details).where(p.details.c.id==relationship['id']).values(disposition='relationship',last_substantive_at=p.months(at,-24),
            retention_exception_ref='fixture_contract_review',retention_exception_until=at+timedelta(days=1)))
    with Session(engine) as db:
        before=p.retention_preview(db,org,at-timedelta(seconds=1))['items']
        assert not any(i['inquiry_id']==str(spam['id']) for i in before)
        items={i['inquiry_id']:i['action'] for i in p.retention_preview(db,org,at)['items']}
        assert items[str(spam['id'])]=='erase' and items[str(relationship['id'])]=='retained_exception'
        expired={i['inquiry_id']:i['action'] for i in p.retention_preview(db,org,at+timedelta(days=1))['items']}
        assert expired[str(relationship['id'])]=='erase'
