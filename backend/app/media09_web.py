"""Public synthetic staging form and session-authenticated inbox on existing Media API.
Production and real-data intake remain disabled pending owner privacy approval.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from . import human_auth, media09_press as press
from .contact_service import config, session
from .hubspot import HubSpot
from .persistence.audit import audit_events
from .persistence.media09 import press_inquiry_details as details

router = APIRouter()
ASSETS = Path(__file__).parent / 'media09_assets'
COOKIE = '__Host-sc_press_form'

def enabled():
    if os.getenv('SCEC_MEDIA09_WEB_STAGING_ENABLED') != '1' or os.getenv('SCEC_MEDIA09_PRESS_STAGING_ENABLED') != '1' or os.getenv('SCEC_ENV', 'production') == 'production':
        raise HTTPException(503, 'Press inquiry service is awaiting release approval')
    config()

def tenant():
    enabled()
    try:
        value = UUID(os.environ['SCEC_MEDIA09_PUBLIC_ORGANIZATION_ID'])
        if str(value) not in config()[1]: raise ValueError()
        return value
    except (ValueError, KeyError):
        raise HTTPException(503, 'Press organization not configured') from None

def origin(request):
    expected = os.getenv('SCEC_MEDIA09_ORIGIN', '')
    if not expected.startswith('https://') or request.headers.get('origin') != expected:
        raise HTTPException(403, 'Origin mismatch')

def form_token():
    raw = str(int(time.time())+1800)+'.'+secrets.token_urlsafe(24)
    return raw+'.'+hmac.new(press_secret(), raw.encode(), hashlib.sha256).hexdigest()

def press_secret():
    key = os.getenv('SCEC_IDENTITY_SIGNING_KEY','')
    if len(key)<32: raise HTTPException(503, 'Form protection not configured')
    return key.encode()

def verify_form(request):
    origin(request)
    value = request.headers.get('x-sc-form','')
    if len(value)>200 or not value or not hmac.compare_digest(value, request.cookies.get(COOKIE,'')):
        raise HTTPException(403,'Reload the form before submitting')
    try:
        expiry, nonce, signature = value.split('.')
        raw = expiry+'.'+nonce
        if not int(time.time()) < int(expiry) <= int(time.time())+1800 or not hmac.compare_digest(signature,hmac.new(press_secret(),raw.encode(),hashlib.sha256).hexdigest()):
            raise ValueError()
    except ValueError:
        raise HTTPException(403,'Reload the form before submitting') from None

@router.get('/press/', response_class=HTMLResponse)
def public_page():
    tenant()
    token = form_token()
    response = HTMLResponse((ASSETS/'press.html').read_text().replace('FORM_TOKEN',token))
    response.set_cookie(COOKIE, token, secure=True, httponly=True, samesite='strict', max_age=1800, path='/')
    return response

@router.post('/press/inquiries')
async def public_submit(request: Request, db: Session=Depends(session)):
    org=tenant(); verify_form(request)
    # Read at most 8 KiB, regardless of whether Content-Length was supplied.
    body=bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body)>8192: raise HTTPException(413,'Submission too large')
    try:
        payload=press.PressInquiryCreate.model_validate_json(body)
    except (ValidationError, ValueError):
        raise HTTPException(422,'Use synthetic test details only; check the required fields') from None
    result=press.create_record(db,org,payload)
    return JSONResponse(result,status_code=201 if result['created'] else 200)


def staff(request: Request):
    enabled()
    cfg=human_auth.config()
    record=human_auth.current_session(request,cfg)
    org, roles=human_auth.resolve_member(record['subject'])
    # Recheck current membership on every request, including after role removal.
    if org != record['organization_id'] or not set(roles).intersection({'contact_editor','administrator'}):
        raise HTTPException(403,'Press staff access required')
    if org not in config()[1]: raise HTTPException(403,'Organization denied')
    if request.method not in ('GET','HEAD'):
        origin(request); human_auth.require_csrf(request,record)
    return UUID(org), record['subject'], set(roles)

@router.get('/press/inbox',response_class=HTMLResponse)
def inbox_page(context=Depends(staff)):
    return HTMLResponse((ASSETS/'inbox.html').read_text())

@router.get('/press/staff/inquiries')
def inbox(context=Depends(staff),db:Session=Depends(session)):
    return press.list_records(db,context[0],50,0)

@router.get('/press/staff/inquiries/{ident}')
def detail(ident:UUID,context=Depends(staff),db:Session=Depends(session)):
    return press.detail_record(db,context[0],ident)

@router.patch('/press/staff/inquiries/{ident}/status')
def review(ident:UUID,payload:press.PressStatusChange,context=Depends(staff),db:Session=Depends(session)):
    if payload.status=='closed' and 'administrator' not in context[2]:
        raise HTTPException(403,'Administrator approval required to close')
    return press.transition_record(db,context[0],ident,payload)

class Assignment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:int=Field(ge=1)
    subject:str | None=Field(default=None,max_length=200)

@router.patch('/press/staff/inquiries/{ident}/assignment')
def assign(ident:UUID,payload:Assignment,context=Depends(staff),db:Session=Depends(session)):
    org,_,_=context
    if payload.subject:
        assigned_org,roles=human_auth.resolve_member(payload.subject)
        if assigned_org!=str(org) or not set(roles).intersection({'contact_editor','administrator'}):
            raise HTTPException(403,'Assignee must be authorized Press staff in this organization')
    with db.begin():
        press._advisory_lock(db,org)
        changed=db.execute(update(details).where(details.c.id==ident,details.c.organization_id==org,
            details.c.version==payload.expected_version,details.c.status!='closed').values(
            assigned_to=payload.subject,version=payload.expected_version+1,updated_at=datetime.now(timezone.utc)))
        if changed.rowcount!=1: raise HTTPException(409,'Inquiry changed or is closed; reload before assigning')
        db.execute(insert(audit_events).values(organization_id=org,record_type='press_inquiries',record_id=ident,
            operation='updated',recorded_at=datetime.now(timezone.utc)))
    return {'assigned':True,'version':payload.expected_version+1}

class SyncApproval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:int=Field(ge=1)
    approved:bool

@router.post('/press/staff/inquiries/{ident}/hubspot')
def sync_contact(ident:UUID,payload:SyncApproval,context=Depends(staff),db:Session=Depends(session)):
    if 'administrator' not in context[2] or not payload.approved:
        raise HTTPException(403,'Explicit administrator export approval required')
    # Live credential/account activation is separate from first-party operation.
    if os.getenv('SCEC_MEDIA09_HUBSPOT_ENABLED')!='1':
        raise HTTPException(503,'Optional HubSpot connector is disconnected')
    path=Path(os.getenv('SCEC_HUBSPOT_TOKEN_FILE',''))
    if not path.is_absolute() or not path.is_file() or path.stat().st_mode & 0o077:
        raise HTTPException(503,'Protected backend HubSpot credential required')
    org=context[0]
    with db.begin():
        press._advisory_lock(db,org)
        row=db.execute(press._joined(org).where(details.c.id==ident)).mappings().first()
        if row is None: raise HTTPException(404,'Inquiry not found')
        if row['version']!=payload.expected_version or row['status']!='reviewing':
            raise HTTPException(409,'Review the current inquiry before export')
        connector=HubSpot(path.read_text().strip())
        try:
            result=connector.sync('contacts',{'email':row['contact']['email'],
                'firstname':row['contact']['display_name']},approved=True)
        finally: connector.close()
        outcome={**asdict(result),'at':datetime.now(timezone.utc).isoformat()}
        db.execute(update(details).where(details.c.id==ident,details.c.organization_id==org).values(
            sync_result=outcome,version=row['version']+1,updated_at=datetime.now(timezone.utc)))
        db.execute(insert(audit_events).values(organization_id=org,record_type='press_inquiries',record_id=ident,
            operation='updated',recorded_at=datetime.now(timezone.utc)))
    return outcome

@router.get('/press/assets/{name}')
def asset(name:str):
    if name not in {'press.css','press.js','inbox.js'}: raise HTTPException(404,'Not found')
    return FileResponse(ASSETS/name)

def install(app):
    @app.middleware('http')
    async def protect(request, call_next):
        response=await call_next(request)
        if request.url.path.startswith('/press/'):
            response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                'Referrer-Policy':'no-referrer','X-Frame-Options':'DENY',
                'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response
    app.include_router(router)
