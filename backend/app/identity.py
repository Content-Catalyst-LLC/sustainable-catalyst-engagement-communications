"""v8.6 opt-in bound service principal authentication.
Compact HMAC-SHA256 tokens. No external IdP, browser login or user identity claims.
Production bound mode requires per-principal tokens with organization, roles and expiry.
"""
import base64
import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass
from uuid import UUID
from fastapi import Header, HTTPException, Depends

LOG=logging.getLogger('scec.access')
ROLES={'viewer','contact_editor','support_agent','advisor','approver','administrator'}
POLICY={
 'contracts:read':{'viewer','contact_editor','support_agent','advisor','approver','administrator'},
 'engagement:read':{'viewer','contact_editor','support_agent','advisor','approver','administrator'},
 'engagement:write':{'contact_editor','administrator'},
 'support:read':{'support_agent','administrator'},
 'support:write':{'support_agent','administrator'},
 'advisory:read':{'advisor','approver','administrator'},
 'advisory:write':{'advisor','administrator'},
 'advisory:request':{'advisor','administrator'},
 'advisory:approve':{'approver','administrator'},
}
@dataclass(frozen=True)
class Principal:
    subject: str
    organization_id: UUID
    roles: frozenset[str]
    expires_at: int

def _decode(v):
    if not v or len(v)>8192:raise ValueError('Invalid encoding')
    return base64.urlsafe_b64decode(v+'='*(-len(v)%4))

def _encode(v):return base64.urlsafe_b64encode(v).rstrip(b'=').decode()

def _secret():
    secret=os.getenv('SCEC_IDENTITY_SIGNING_KEY','')
    if len(secret)<32:raise HTTPException(503,'Bound identity signing key not configured')
    return secret.encode()

def mint_token(*, subject, organization_id, roles, expires_at, secret):
    """Offline deployment/test helper; never offered by an HTTP route."""
    payload={'v':1,'sub':subject,'org':str(organization_id),'roles':sorted(roles),
             'exp':int(expires_at),'aud':'scec-engagement'}
    raw=_encode(json.dumps(payload,sort_keys=True,separators=(',',':')).encode())
    sig=_encode(hmac.new(secret.encode(),raw.encode(),hashlib.sha256).digest())
    return raw+'.'+sig

# Verify the bounded, signed engagement principal token before accepting its
# organization and roles. Invalid signature, audience, expiry or shape returns
# HTTP 401. The legacy identity mode bypasses this parser elsewhere; a token
# check here is not proof that every route runs in bound mode.
def parse_token(token: str, *, now=None):
    try:
        if len(token)>8192:raise ValueError()
        raw,sig=token.split('.')
        expected=hmac.new(_secret(),raw.encode(),hashlib.sha256).digest()
        if not hmac.compare_digest(expected,_decode(sig)):raise ValueError()
        data=json.loads(_decode(raw))
        if not isinstance(data,dict) or data.get('v')!=1 or data.get('aud')!='scec-engagement':raise ValueError()
        sub=data.get('sub');roles=data.get('roles');expiry=data.get('exp')
        if not isinstance(sub,str) or not (1<=len(sub)<=120) or not isinstance(roles,list) or not roles or len(roles)>6 or any(r not in ROLES for r in roles):raise ValueError()
        if type(expiry) is not int or expiry <= (time.time() if now is None else now) or expiry > (time.time() if now is None else now)+86400:raise ValueError()
        org=UUID(data['org'])
        if str(org)!=data['org']:raise ValueError()
        return Principal(sub,org,frozenset(roles),expiry)
    except (ValueError,KeyError,TypeError,UnicodeDecodeError,OverflowError):
        raise HTTPException(401,'Invalid or expired principal token') from None

def bound_mode():return os.getenv('SCEC_IDENTITY_MODE','legacy')=='bound'

def principal(authorization: str|None=Header(default=None)):
    if not bound_mode():return None
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Principal token required')
    return parse_token(authorization[7:])

def require_permission(permission):
    def check(actor: Principal|None=Depends(principal)):
        if not bound_mode():return None
        if actor is None:raise HTTPException(401,'Principal required')
        if not actor.roles.intersection(POLICY[permission]):
            LOG.warning('access_denied action=%s subject_hash=%s',permission,hashlib.sha256(actor.subject.encode()).hexdigest()[:12])
            raise HTTPException(403,'Permission denied')
        return actor
    return check

def tenant_for_principal(header_org: str|None,actor:Principal|None):
    if actor is None:raise HTTPException(401,'Principal required')
    if not header_org or header_org!=str(actor.organization_id):raise HTTPException(403,'Organization does not match authenticated principal')
    return actor.organization_id

def verify_actor_reference(reference: str, actor: Principal|None):
    if bound_mode() and (actor is None or reference!=actor.subject):raise HTTPException(403,'Actor reference must match authenticated principal')
