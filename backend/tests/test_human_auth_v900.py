import json
import sqlite3
import time
from uuid import uuid4
from urllib.parse import urlsplit,parse_qs

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import human_auth as auth

@pytest.fixture
def enabled(monkeypatch,tmp_path):
    data={'SCEC_HUMAN_AUTH_ENABLED':'1','SCEC_OIDC_ISSUER':'https://id.example.test',
          'SCEC_OIDC_CLIENT_ID':'test-client','SCEC_OIDC_CLIENT_SECRET':'test-secret',
          'SCEC_OIDC_AUTH_URL':'https://id.example.test/authorize',
          'SCEC_OIDC_TOKEN_URL':'https://id.example.test/token',
          'SCEC_OIDC_JWKS_URL':'https://id.example.test/keys',
          'SCEC_OIDC_REDIRECT_URI':'https://auth.example.test/v1/human-auth/callback',
          'SCEC_HUMAN_AUTH_ORIGIN':'https://auth.example.test',
          'SCEC_HUMAN_SESSION_DB':str(tmp_path/'sessions.db'),'SCEC_PERSISTENCE_ENABLED':'0'}
    for k,v in data.items():monkeypatch.setenv(k,v)
    return data

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SCEC_HUMAN_AUTH_ENABLED',raising=False)
    assert TestClient(app).get('/v1/human-auth/login').status_code==503

def test_config_requires_secure_origin(enabled,monkeypatch):
    monkeypatch.setenv('SCEC_OIDC_AUTH_URL','http://id.example.test/authorize')
    assert TestClient(app).get('/v1/human-auth/login').status_code==503

def test_no_operational_writes_when_human_auth_enabled(enabled,monkeypatch):
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    assert TestClient(app).get('/v1/human-auth/login').status_code==503

def test_pkce_nonce_state_and_cookie(enabled):
    client=TestClient(app,follow_redirects=False)
    response=client.get('/v1/human-auth/login')
    assert response.status_code==302
    query=parse_qs(urlsplit(response.headers['location']).query)
    assert query['code_challenge_method']==['S256']
    assert query['nonce'][0]
    assert query['state'][0]
    assert 'Secure' in response.headers['set-cookie']
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.get('/v1/human-auth/callback?code=fake&state=wrong').status_code==401

def test_membership_denial_and_role_source(enabled,monkeypatch):
    assert TestClient(app).get('/v1/human-auth/session').status_code==401
    with pytest.raises(Exception) as exc:auth.resolve_member('random-subject')
    assert exc.value.status_code==403
    organization=str(uuid4())
    monkeypatch.setenv('SCEC_HUMAN_MEMBERSHIPS',json.dumps({'idp|subject':{'organization_id':organization,'roles':['viewer']}}))
    assert auth.resolve_member('idp|subject')==(organization,['viewer'])

def test_session_revocation_tenant_role_csrf(enabled):
    cfg=auth.config();token='example-server-only-token';csrf='a'*48;org=str(uuid4());now=int(time.time())
    with auth.store(cfg) as db:
        db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?)',
                   (auth.digest(token),'subject-123',org,json.dumps(['viewer']),auth.digest(csrf),now+300))
        db.commit()
    client=TestClient(app,follow_redirects=False)
    client.cookies.set(auth.SESSION_COOKIE,token)
    assert client.get('/v1/human-auth/session').status_code==200
    assert client.get('/v1/human-auth/authorization-check',params={'permission':'engagement:read','organization_id':org}).status_code==200
    assert client.get('/v1/human-auth/authorization-check',params={'permission':'engagement:write','organization_id':org}).status_code==403
    assert client.get('/v1/human-auth/authorization-check',params={'permission':'engagement:read','organization_id':str(uuid4())}).status_code==403
    assert client.post('/v1/human-auth/logout').status_code==403
    headers={'Origin':'https://auth.example.test',auth.CSRF_HEADER:csrf}
    assert client.post('/v1/human-auth/logout',headers=headers).status_code==204
    assert client.get('/v1/human-auth/session').status_code==401

def test_sessions_not_connected_to_legacy_writes(enabled):
    client=TestClient(app)
    assert client.post('/v1/engagement/contacts',json={'name':'attempt'}).status_code in (401,403,503)
