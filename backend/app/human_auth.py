"""v9.0.0 opt-in OIDC identity boundary. Does not authorize legacy data writes.

Requires trusted external OIDC IdP and explicit subject-to-membership mapping.
SQLite is an intentionally single-node *staging* session store, not HA-certified.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlencode, urlparse
from uuid import UUID

import httpx
import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

router = APIRouter(prefix='/v1/human-auth', tags=['staged-human-auth'])
SESSION_COOKIE = '__Host-scec_session'
FLOW_COOKIE = '__Host-scec_login'
CSRF_HEADER = 'x-scec-csrf'
ALLOWED_ROLES = {'viewer','contact_editor','support_agent','advisor','approver','administrator'}


def config():
    if os.getenv('SCEC_HUMAN_AUTH_ENABLED') != '1':
        raise HTTPException(503, 'Human authentication not configured')
    keys = ['SCEC_OIDC_ISSUER','SCEC_OIDC_CLIENT_ID','SCEC_OIDC_CLIENT_SECRET',
            'SCEC_OIDC_AUTH_URL','SCEC_OIDC_TOKEN_URL','SCEC_OIDC_JWKS_URL',
            'SCEC_OIDC_REDIRECT_URI','SCEC_HUMAN_AUTH_ORIGIN','SCEC_HUMAN_SESSION_DB']
    vals = {k:os.getenv(k,'').strip() for k in keys}
    if any(not v for v in vals.values()):
        raise HTTPException(503, 'OIDC configuration incomplete')
    for k in ['SCEC_OIDC_ISSUER','SCEC_OIDC_AUTH_URL','SCEC_OIDC_TOKEN_URL',
              'SCEC_OIDC_JWKS_URL','SCEC_OIDC_REDIRECT_URI','SCEC_HUMAN_AUTH_ORIGIN']:
        parsed=urlparse(vals[k]);
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            raise HTTPException(503, 'OIDC HTTPS configuration invalid')
    if vals['SCEC_OIDC_REDIRECT_URI'] != vals['SCEC_HUMAN_AUTH_ORIGIN'].rstrip('/') + '/v1/human-auth/callback':
        raise HTTPException(503, 'OIDC callback/origin mismatch')
    if os.getenv('SCEC_PERSISTENCE_ENABLED','0') != '0':
        raise HTTPException(503, 'Staging human auth requires production writes disabled')
    return vals


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def store(cfg):
    path=cfg['SCEC_HUMAN_SESSION_DB']
    if path == ':memory:' or not os.path.isabs(path):
        raise HTTPException(503,'Absolute session database path required')
    db=sqlite3.connect(path, timeout=5)
    try:
        db.execute('PRAGMA busy_timeout=5000')
        db.execute('CREATE TABLE IF NOT EXISTS flows (key TEXT PRIMARY KEY, verifier TEXT NOT NULL, nonce TEXT NOT NULL, expires INTEGER NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (key TEXT PRIMARY KEY, subject TEXT NOT NULL, organization TEXT NOT NULL, roles TEXT NOT NULL, csrf_hash TEXT NOT NULL, expires INTEGER NOT NULL)')
        db.commit()
        yield db
    finally: db.close()


def memberships():
    """Subject membership is server-owned; no ID-token roles automatically trusted."""
    try: values=json.loads(os.getenv('SCEC_HUMAN_MEMBERSHIPS','{}'))
    except ValueError:raise HTTPException(503,'Membership configuration invalid')
    if not isinstance(values,dict):raise HTTPException(503,'Membership configuration invalid')
    return values


def resolve_member(subject):
    member=memberships().get(subject)
    if not isinstance(member,dict):raise HTTPException(403,'Account not provisioned')
    try:
        org=str(UUID(member['organization_id']))
        roles=member['roles']
        if not isinstance(roles,list) or not roles or len(roles)>6 or not set(roles).issubset(ALLOWED_ROLES):raise ValueError()
    except (ValueError,KeyError,TypeError):raise HTTPException(403,'Invalid account provisioning')
    return org,sorted(set(roles))


def set_cookie(response, name, value, seconds, path='/'):
    response.set_cookie(name,value, max_age=seconds, path=path, secure=True, httponly=True,
                        samesite='lax')


def origin_ok(request, origin):
    if request.headers.get('origin') != origin.rstrip('/'):
        raise HTTPException(403,'Origin mismatch')


def current_session(request, cfg):
    token=request.cookies.get(SESSION_COOKIE,'')
    if not token or len(token)>128:raise HTTPException(401,'Human session required')
    with store(cfg) as db:
        row=db.execute('SELECT subject,organization,roles,csrf_hash,expires FROM sessions WHERE key=?',(digest(token),)).fetchone()
    if not row or row[4]<=int(time.time()):raise HTTPException(401,'Session expired or revoked')
    return {'subject':row[0],'organization_id':row[1],'roles':json.loads(row[2]),'csrf_hash':row[3],'expires':row[4]}


def require_csrf(request, session):
    token=request.headers.get(CSRF_HEADER,'')
    if len(token)<32 or not hmac.compare_digest(digest(token), session['csrf_hash']):
        raise HTTPException(403,'CSRF validation failed')


@router.get('/login')
def login():
    cfg=config()
    state=secrets.token_urlsafe(32); nonce=secrets.token_urlsafe(32); verifier=secrets.token_urlsafe(48)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    with store(cfg) as db:
        db.execute('DELETE FROM flows WHERE expires < ?',(int(time.time()),))
        db.execute('INSERT INTO flows VALUES(?,?,?,?)',(digest(state),verifier,nonce,int(time.time())+300))
        db.commit()
    query=urlencode({'response_type':'code','client_id':cfg['SCEC_OIDC_CLIENT_ID'],
                     'redirect_uri':cfg['SCEC_OIDC_REDIRECT_URI'],'scope':'openid',
                     'state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256'})
    response=RedirectResponse(cfg['SCEC_OIDC_AUTH_URL']+'?'+query,status_code=302)
    set_cookie(response,FLOW_COOKIE,state,300)
    response.headers['Cache-Control']='no-store'
    return response


# Complete OIDC authorization-code/PKCE login after matching the flow cookie
# and stored state, then issue a short-lived local session with separate CSRF
# material. This consumes the stored flow and writes a session; provider or
# state failures return 401. Same-origin proxy/cookie behavior must still be
# verified in the deployed environment.
@router.get('/callback')
def callback(request:Request, code:str='', state:str='', error:str=''):
    cfg=config()
    if error or not code or len(code)>4096 or not state or len(state)>128:
        raise HTTPException(401,'OIDC sign-in unsuccessful')
    cookie=request.cookies.get(FLOW_COOKIE,'')
    if not cookie or not hmac.compare_digest(cookie,state):raise HTTPException(401,'OIDC state mismatch')
    with store(cfg) as db:
        row=db.execute('SELECT verifier,nonce,expires FROM flows WHERE key=?',(digest(state),)).fetchone()
        db.execute('DELETE FROM flows WHERE key=?',(digest(state),))
        db.commit()
    if not row or row[2]<=int(time.time()):raise HTTPException(401,'OIDC login expired')
    try:
        with httpx.Client(timeout=8,follow_redirects=False) as client:
            result=client.post(cfg['SCEC_OIDC_TOKEN_URL'],data={'grant_type':'authorization_code',
              'code':code,'redirect_uri':cfg['SCEC_OIDC_REDIRECT_URI'],'client_id':cfg['SCEC_OIDC_CLIENT_ID'],
              'client_secret':cfg['SCEC_OIDC_CLIENT_SECRET'],'code_verifier':row[0]})
            result.raise_for_status()
            id_token=result.json()['id_token']
        key=PyJWKClient(cfg['SCEC_OIDC_JWKS_URL'],cache_keys=True,lifespan=300).get_signing_key_from_jwt(id_token).key
        claims=jwt.decode(id_token,key,algorithms=['RS256'],audience=cfg['SCEC_OIDC_CLIENT_ID'],
                          issuer=cfg['SCEC_OIDC_ISSUER'],options={'require':['exp','iat','iss','aud','sub']},leeway=30)
        if not hmac.compare_digest(str(claims.get('nonce','')),row[1]):raise ValueError('nonce')
        sub=claims['sub']
        if not isinstance(sub,str) or not (1<=len(sub)<=200):raise ValueError('subject')
    except (httpx.HTTPError,KeyError,ValueError,jwt.PyJWTError) as exc:
        raise HTTPException(401,'OIDC verification failed') from None
    org,roles=resolve_member(sub)
    token=secrets.token_urlsafe(48); csrf=secrets.token_urlsafe(48)
    expires=int(time.time())+max(60,min(3600,int(os.getenv('SCEC_HUMAN_SESSION_MAX_SECONDS','1800'))))
    with store(cfg) as db:
        db.execute('DELETE FROM sessions WHERE expires < ?',(int(time.time()),))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',
                   (digest(token),sub,org,json.dumps(roles),digest(csrf),expires))
        db.commit()
    response=RedirectResponse(cfg['SCEC_HUMAN_AUTH_ORIGIN'].rstrip('/')+'/v1/human-auth/session',status_code=303)
    set_cookie(response,SESSION_COOKIE,token,expires-int(time.time()))
    response.delete_cookie(FLOW_COOKIE,path='/',secure=True,httponly=True,samesite='lax')
    # CSRF token issued only to the same-origin callback client via non-HttpOnly *separate* cookie.
    response.set_cookie('__Host-scec_csrf',csrf,max_age=expires-int(time.time()),secure=True,
                        httponly=False,samesite='strict',path='/')
    response.headers['Cache-Control']='no-store'
    return response


@router.get('/session')
def session(request:Request):
    cfg=config(); record=current_session(request,cfg)
    response=Response(content=json.dumps({'authenticated':True,'organization_id':record['organization_id'],
                                          'roles':record['roles'],'expires':record['expires']}),
                      media_type='application/json')
    response.headers['Cache-Control']='no-store'
    return response


@router.post('/logout')
def logout(request:Request):
    cfg=config();origin_ok(request,cfg['SCEC_HUMAN_AUTH_ORIGIN'])
    record=current_session(request,cfg);require_csrf(request,record)
    token=request.cookies[SESSION_COOKIE]
    with store(cfg) as db:
        db.execute('DELETE FROM sessions WHERE key=?',(digest(token),));db.commit()
    response=Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE,path='/',secure=True,httponly=True,samesite='lax')
    response.delete_cookie('__Host-scec_csrf',path='/',secure=True,samesite='strict')
    response.headers['Cache-Control']='no-store'
    return response


@router.post('/session/revoke-all')
def revoke_all(request:Request):
    cfg=config();origin_ok(request,cfg['SCEC_HUMAN_AUTH_ORIGIN'])
    record=current_session(request,cfg);require_csrf(request,record)
    with store(cfg) as db:
        db.execute('DELETE FROM sessions WHERE subject=?',(record['subject'],));db.commit()
    response=Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE,path='/',secure=True,httponly=True,samesite='lax')
    response.delete_cookie('__Host-scec_csrf',path='/',secure=True,samesite='strict')
    return response


@router.get('/authorization-check')
def authorization_check(request:Request, permission:str, organization_id:str):
    cfg=config();record=current_session(request,cfg)
    from .identity import POLICY
    if permission not in POLICY:raise HTTPException(400,'Unknown permission')
    if not hmac.compare_digest(organization_id,record['organization_id']):raise HTTPException(403,'Tenant mismatch')
    if not set(record['roles']).intersection(POLICY[permission]):raise HTTPException(403,'Insufficient role')
    return {'allowed':True,'permission':permission,'organization_id':record['organization_id']}
