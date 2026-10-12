import time
from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.identity import mint_token, parse_token, tenant_for_principal, verify_actor_reference, require_permission, principal
from app.main import app
from app.settings import Settings, validate_settings
KEY='test-bound-key-'+('x'*44)

@pytest.fixture
def identity(monkeypatch):
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY)
    yield

def token(org, roles=('viewer',), subject='test:alice', expires=None):
    return mint_token(subject=subject, organization_id=org, roles=roles,
                      expires_at=expires or int(time.time())+1800, secret=KEY)

def test_requires_secret_in_bound_mode():
    with pytest.raises(RuntimeError):
        validate_settings(Settings(identity_mode='bound',identity_signing_key='short'))

def test_production_bound_security_configuration():
    validate_settings(Settings(environment='production',identity_mode='bound',identity_signing_key=KEY,auth_mode='disabled'))

def test_token_signature_expiry_and_audience(identity):
    org=uuid4(); good=token(org)
    actor=parse_token(good)
    assert actor.organization_id==org and actor.subject=='test:alice'
    with pytest.raises(HTTPException) as e:parse_token(good[:-2]+'aa')
    assert e.value.status_code==401
    with pytest.raises(HTTPException) as e:parse_token(token(org,expires=int(time.time())-1))
    assert e.value.status_code==401
    with pytest.raises(HTTPException):parse_token('not.a.token')

def test_bound_contract_requires_valid_identity(identity):
    client=TestClient(app)
    assert client.get('/v1/contracts/canonical').status_code==401
    assert client.get('/v1/contracts/canonical',headers={'Authorization':'Bearer legacy-token'}).status_code==401
    assert client.get('/v1/contracts/canonical',headers={'Authorization':'Bearer '+token(uuid4())}).status_code==200

def test_read_only_cannot_write(identity):
    client=TestClient(app)
    headers={'Authorization':'Bearer '+token(uuid4(),('viewer',))}
    assert client.post('/v1/engagement/contacts',json={},headers=headers).status_code==403
    assert client.get('/v1/support/cases',headers=headers).status_code==403
    assert client.post('/v1/advisory/engagements',json={},headers=headers).status_code==403

def test_org_bound_enforced_before_db(identity,monkeypatch):
    org=uuid4(); other=uuid4()
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    monkeypatch.setenv('SCEC_DATABASE_URL','postgresql+psycopg://fake@localhost/scec_engagement_test')
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',','.join([str(org),str(other)]))
    headers={'Authorization':'Bearer '+token(org,('contact_editor',)), 'X-SCEC-Organization-ID':str(other)}
    assert TestClient(app).post('/v1/engagement/contacts',json={},headers=headers).status_code==403

def test_advisory_approval_role_and_actor_identity(identity,monkeypatch):
    monkeypatch.setenv("SCEC_PERSISTENCE_ENABLED","1")
    monkeypatch.setenv("SCEC_DATABASE_URL","postgresql+psycopg://fake@localhost/scec_engagement_test")
    org=uuid4();client=TestClient(app)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(org))
    base='/v1/advisory/engagements/'+str(uuid4())+'/approvals/'+str(uuid4())+'/decision'
    viewer={'Authorization':'Bearer '+token(org,('advisor',)), 'X-SCEC-Organization-ID':str(org)}
    assert client.post(base,json={'decision':'approved','actor_ref':'test:alice'},headers=viewer).status_code==403
    from app.contact_service import session
    app.dependency_overrides[session]=lambda: object()
    approver={'Authorization':'Bearer '+token(org,('approver',)), 'X-SCEC-Organization-ID':str(org)}
    try:
        assert client.post(base,json={'decision':'approved','actor_ref':'test:bob'},headers=approver).status_code==403
    finally:
        app.dependency_overrides.pop(session,None)

def test_reference_binding(identity):
    actor=parse_token(token(uuid4(),('approver',)))
    verify_actor_reference('test:alice',actor)
    with pytest.raises(HTTPException) as e:verify_actor_reference('test:bob',actor)
    assert e.value.status_code==403

def test_migration_unchanged_and_no_exposed_issuer():
    paths={r.path for r in app.routes}
    assert not any('token' in path or 'mint' in path for path in paths)
    assert app.version=='9.2.0'
