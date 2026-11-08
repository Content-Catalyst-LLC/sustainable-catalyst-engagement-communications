"""MEDIA-06 security/state tests; all records use isolated in-memory SQLite.
No Contabo, Bluehost, production DB, email, social account, or external network.
"""
import hashlib
import json
import time
from uuid import uuid4
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.main import app
from app.media_operations_v1260 import database, meta, packages
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

ORG='00000000-0000-4000-8000-000000000001'
OTHER='00000000-0000-4000-8000-000000000002'

def package(hash_value='b'):
    return {
        'schema_version':'scec.media-bridge/1','organization_id':ORG,
        'package_ref':'wp-media:101','source_url':'https://sustainablecatalyst.com/paper/',
        'source_content_sha256':'a'*64,'approved_package_sha256':hash_value*64,
        'approved_at_utc':'2026-11-08T00:00:00+00:00',
        'channels':['substack','linkedin'],'source_published_attested':True,
        'rights_review_attested':True,'embargo_review_attested':True,
        'export_mode':'metadata_preview_only',
    }

def submit(hash_value='b',actor='wp:user:11',key=None):
    return {'package':package(hash_value),'submitted_by':actor,
            'idempotency_key':key or hashlib.sha256((hash_value+actor).encode()).hexdigest()}

@pytest.fixture
def staging(tmp_path,monkeypatch):
    for flag in (*DANGER_FLAGS, *EXTRA_DANGER_FLAGS):
        monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_ENV','staging')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_MEDIA06_ENABLED','1')
    monkeypatch.setenv('SCEC_MEDIA06_STORAGE_ENABLED','1')
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS', ORG)
    monkeypatch.setenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS','sustainablecatalyst.com')
    monkeypatch.setenv('SCEC_MEDIA06_DATABASE_URL','postgresql+psycopg://test@localhost/scec_engagement_test')
    monkeypatch.setenv('SCEC_MEDIA06_ISSUER','https://sustainablecatalyst.com')
    key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    pub=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    pubfile=tmp_path/'keys.json'
    pubfile.write_text(json.dumps({'bluehost_test_2026':pub}))
    pubfile.chmod(0o600)
    monkeypatch.setenv('SCEC_MEDIA06_PUBLIC_KEYS_FILE',str(pubfile))
    engine=create_engine('sqlite+pysqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    meta.create_all(engine)
    def local_db():
        with Session(engine) as session:
            yield session
    app.dependency_overrides[database]=local_db
    try:
        yield TestClient(app),pem
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

def request(staging,method,path,payload=None,org=ORG,claims_override=None):
    client,key=staging
    body = b'' if payload is None else json.dumps(payload,separators=(',',':')).encode()
    current=int(time.time())
    claims={'iss':'https://sustainablecatalyst.com','aud':'scec-media06',
            'sub':'wordpress:media-ops','org':org,'iat':current,'nbf':current-1,
            'exp':current+90,'jti':str(uuid4()),'method':method,'path':path,
            'body_sha256':hashlib.sha256(body).hexdigest()}
    claims.update(claims_override or {})
    token=jwt.encode(claims,key,algorithm='RS256',headers={'kid':'bluehost_test_2026'})
    headers={'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':org,'Content-Type':'application/json'}
    return client.request(method,path,content=body if method=='POST' else None,headers=headers)

def test_status_requires_explicit_staging_and_signed_request(staging,monkeypatch):
    client,_=staging
    assert client.get('/v1/media-ops/status').status_code==401
    good=request(staging,'GET','/v1/media-ops/status')
    assert good.status_code==200
    assert good.json()['sending_enabled'] is False
    assert good.json()['human_identity_federated'] is False
    monkeypatch.setenv('SCEC_MEDIA06_ENABLED','0')
    assert request(staging,'GET','/v1/media-ops/status').status_code==503

def test_assertion_bound_to_method_path_body_tenant_and_expiry(staging):
    assert request(staging,'GET','/v1/media-ops/status',claims_override={'method':'POST'}).status_code==401
    assert request(staging,'GET','/v1/media-ops/status',claims_override={'body_sha256':'0'*64}).status_code==401
    assert request(staging,'GET','/v1/media-ops/status',claims_override={'org':OTHER}).status_code==403
    assert request(staging,'GET','/v1/media-ops/status',claims_override={'exp':int(time.time())-60}).status_code==401
    assert request(staging,'GET','/v1/media-ops/status',claims_override={'exp':int(time.time())+3600}).status_code==401

def test_storage_requires_opt_in(staging,monkeypatch):
    from app.media_operations_v1260 import require_storage
    from fastapi import HTTPException
    monkeypatch.setenv('SCEC_MEDIA06_STORAGE_ENABLED','0')
    with pytest.raises(HTTPException) as err: require_storage()
    assert err.value.status_code==503
    monkeypatch.setenv('SCEC_MEDIA06_STORAGE_ENABLED','1')
    monkeypatch.setenv('SCEC_MEDIA06_DATABASE_URL','postgresql+psycopg://test@localhost/production')
    with pytest.raises(HTTPException) as err: require_storage()
    assert err.value.status_code==503

def test_idempotency_two_distinct_reviewers_audit_and_reconciliation(staging):
    r=request(staging,'POST','/v1/media-ops/packages',submit())
    assert r.status_code==201,r.text
    p=r.json();pkg_id=p['package_id']
    assert p['state']=='in_review'
    replay=request(staging,'POST','/v1/media-ops/packages',submit())
    assert replay.status_code==201 and replay.json()['package_id']==pkg_id
    changed=submit('c',key=submit()['idempotency_key'])
    assert request(staging,'POST','/v1/media-ops/packages',changed).status_code==409
    path='/v1/media-ops/packages/'+pkg_id+'/reviews'
    def review(actor,decision='approve'):
        return request(staging,'POST',path,{'actor_ref':actor,'decision':decision,
            'approved_package_sha256':'b'*64})
    assert review('wp:user:11').status_code==403
    assert review('wp:user:12').json()['state']=='in_review'
    assert review('wp:user:12').status_code==409
    assert review('wp:user:13').json()['state']=='approved'
    assert review('wp:user:14').status_code==409
    url='/v1/media-ops/packages/'+pkg_id
    assert request(staging,'GET',url).json()['state']=='approved'
    audit=request(staging,'GET',url+'/audit').json()['items']
    assert [entry['action'] for entry in audit]==['registered','reviewed','reviewed']
    matched=request(staging,'GET',url+'/reconcile?approved_sha256='+'b'*64).json()
    assert matched['fingerprint_matches'] is True and matched['requires_new_review'] is False
    stale=request(staging,'GET',url+'/reconcile?approved_sha256='+'c'*64).json()
    assert stale['fingerprint_matches'] is False and stale['requires_new_review'] is True

def test_revision_supersedes_previous_and_prevents_stale_review(staging):
    first=request(staging,'POST','/v1/media-ops/packages',submit()).json()
    later=request(staging,'POST','/v1/media-ops/packages',submit('c'))
    assert later.status_code==201,later.text
    old=request(staging,'GET','/v1/media-ops/packages/'+first['package_id']).json()
    assert old['state']=='superseded'
    path='/v1/media-ops/packages/'+first['package_id']+'/reviews'
    response=request(staging,'POST',path,{'actor_ref':'wp:user:12','decision':'approve',
                                          'approved_package_sha256':'b'*64})
    assert response.status_code==409

def test_reject_and_wrong_tenant_and_invalid_inputs(staging):
    r=request(staging,'POST','/v1/media-ops/packages',submit())
    assert r.status_code==201
    pkg_id=r.json()['package_id']
    url='/v1/media-ops/packages/'+pkg_id
    assert request(staging,'GET',url,org=OTHER).status_code==403
    reject=request(staging,'POST',url+'/reviews',{'actor_ref':'wp:user:15',
        'decision':'reject','approved_package_sha256':'b'*64})
    assert reject.status_code==200 and reject.json()['state']=='rejected'
    assert request(staging,'POST','/v1/media-ops/packages',
        {**submit(),'contact_email':'person@example.com'}).status_code==422

@pytest.mark.parametrize('action',['publish','send','schedule','enqueue'])
def test_external_dispatch_stays_blocked(staging,action):
    response=request(staging,'POST','/v1/media-ops/'+action,{})
    assert response.status_code==503
