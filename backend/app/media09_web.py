"""Public synthetic staging form and session-authenticated inbox on existing Media API.
Production and real-data intake remain disabled pending owner privacy approval.
"""
from dataclasses import asdict
from html import escape
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from . import human_auth, media09_press as press
from .contact_service import config, session
from .hubspot import HubSpot
from .media09_release import real_intake, approved_notice
from .media09_rights import RightsReview,Correction,HoldCreate
from .persistence.audit import audit_events
from .persistence.media09 import press_inquiry_details as details

router = APIRouter(route_class=press.RedactedPressRoute)
ASSETS = Path(__file__).parent / 'media09_assets'
COOKIE = '__Host-sc_press_form'

def enabled():
    if real_intake():
        approved_notice()
        config()
        return
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
    page=(ASSETS/'press.html').read_text().replace('FORM_TOKEN',token)
    if real_intake():
        notice=approved_notice()
        start=page.index('<div class="notice"')
        end=page.index('</div>',start)+len('</div>')
        page=page[:start]+'<div class="notice" id="privacy">'+escape(notice['text'])+' <a href="'+escape(notice['privacy_url'],quote=True)+'">Privacy policy</a></div>'+page[end:]
        page=page.replace('content="noindex,nofollow"','content="index,follow"')
        page=page.replace('<form id="inquiry"', '<form data-mode="real" data-notice="'+escape(notice['version'],quote=True)+'" id="inquiry"')
        for a,b in [('Test name','Name'),('Test email','Email'),('Synthetic Press Person','Your name'),('press@example.org','you@institution.org'),('Submit test inquiry','Submit inquiry'),('staging privacy notice and am submitting synthetic test information only.','privacy notice.'),('Use synthetic text only. No HTML, links, or contact details in the message.','Do not include sensitive personal information or private research. No HTML or links.')]:
            page=page.replace(a,b)
    response = HTMLResponse(page)
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
        payload=(press.RealPressInquiryCreate if real_intake() else press.PressInquiryCreate).model_validate_json(body)
    except (ValidationError, ValueError):
        raise HTTPException(422,'Check the required fields and current privacy notice' if real_intake() else 'Use synthetic test details only; check the required fields') from None
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
def inbox_page(request:Request):
    try:
        staff(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return RedirectResponse('/v1/human-auth/login',status_code=303)
        raise
    return HTMLResponse((ASSETS/'inbox.html').read_text().replace('Private · Synthetic staging','Private · Press inquiries') if real_intake() else (ASSETS/'inbox.html').read_text())

@router.get('/press/staff/inquiries')
def inbox(offset:int=Query(0,ge=0,le=100000),context=Depends(staff),db:Session=Depends(session)):
    return press.list_records(db,context[0],50,offset)

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
        from .media09_privacy import assert_record
        assert_record(db,org,"inquiries",ident)
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
    if not os.getenv('SCEC_MEDIA09_HUBSPOT_PRIVACY_APPROVAL_REF'):
        raise HTTPException(503,'Separate HubSpot privacy authorization required')
    path=Path(os.getenv('SCEC_HUBSPOT_TOKEN_FILE',''))
    if path.is_symlink() or not path.is_absolute() or not path.is_file() or path.stat().st_mode & 0o077:
        raise HTTPException(503,'Protected backend HubSpot credential required')
    org=context[0]
    with db.begin():
        press._advisory_lock(db,org)
        from .media09_privacy import assert_record
        assert_record(db,org,"inquiries",ident)
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

@router.get('/press/health')
def press_health(db:Session=Depends(session)):
    enabled()
    from .media09_privacy import guard
    guard(db,tenant())
    try:
        db.execute(select(details.c.id).limit(1)).first()
    except SQLAlchemyError:
        raise HTTPException(503,'Press storage unavailable') from None
    return {'status':'ok','synthetic_only':not real_intake(),'public_personal_data_enabled':real_intake()}

@router.get('/press/assets/{name}')
def asset(name:str):
    if name not in {'press.css','press.js','inbox.js','rights.js','privacy.js'}: raise HTTPException(404,'Not found')
    return FileResponse(ASSETS/name)

def install(app):
    @app.middleware('http')
    async def protect(request, call_next):
        try:
            response=await call_next(request)
        except SQLAlchemyError:
            if not request.url.path.startswith('/press/'):
                raise
            response=JSONResponse({'detail':'Press storage unavailable'},status_code=503)
        if request.url.path.startswith('/press/'):
            response.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff',
                'Referrer-Policy':'no-referrer','X-Frame-Options':'DENY',
                'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response
    app.include_router(router)

# Administrator-only privacy desk shares the existing OIDC session and CSRF.
def privacy_staff(context=Depends(staff)):
    if 'administrator' not in context[2]:raise HTTPException(403,'Privacy administrator required')
    from .media09_privacy import enabled as privacy_enabled
    privacy_enabled()
    return context

@router.get('/press/privacy',response_class=HTMLResponse)
def privacy_page(context=Depends(privacy_staff)):
    return HTMLResponse((ASSETS/'privacy.html').read_text())

@router.get('/press/privacy/rights',response_class=HTMLResponse)
def rights_page():
    tenant()
    from .media09_privacy import enabled as privacy_enabled
    privacy_enabled()
    token=form_token()
    page=(ASSETS/'rights.html').read_text().replace('FORM_TOKEN',token)
    if real_intake():
        page=page.replace('data-mode="synthetic"','data-mode="real"').replace('Synthetic staging only. Use a reserved example.org, example.test or example.invalid address. Do not submit real personal data.', 'Please review our privacy policy before submitting your request. We will verify identity proportionately before acting on it.')
    response=HTMLResponse(page)
    response.set_cookie(COOKIE,token,secure=True,httponly=True,samesite='strict',max_age=1800,path='/')
    return response

@router.post('/press/privacy/requests')
async def rights_intake(request:Request,db:Session=Depends(session)):
    from . import media09_rights as rights
    org=tenant();verify_form(request)
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>2048:raise HTTPException(413,'Rights request too large')
    try:payload=rights.RightsCreate.model_validate_json(data)
    except (ValidationError,ValueError):raise HTTPException(422,'Invalid rights request') from None
    if payload.synthetic==real_intake():raise HTTPException(422,'Request mode does not match release mode')
    with db.begin():return rights.create(db,org,payload)

@router.get('/press/staff/privacy/requests')
def rights_queue(offset:int=Query(0,ge=0,le=100000),context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_rights import queue
    return queue(db,context[0],offset)

@router.patch('/press/staff/privacy/requests/{ident}')
def rights_review(ident:UUID,payload:RightsReview,
                 context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_rights import review
    with db.begin():return review(db,context[0],ident,payload)

@router.get('/press/staff/privacy/requests/{ident}/data')
def rights_export(ident:UUID,context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_rights import subject_data
    return subject_data(db,context[0],ident)

@router.patch('/press/staff/privacy/requests/{ident}/correction')
def rights_correct(ident:UUID,payload:Correction,
                   context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_rights import correct
    with db.begin():return correct(db,context[0],ident,payload)

@router.get('/press/staff/privacy/holds')
def holds(context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_privacy import guard,now,legal_holds
    guard(db,context[0])
    rows=db.execute(select(legal_holds).where(legal_holds.c.organization_id==context[0]).order_by(legal_holds.c.created_at.desc()).limit(100)).mappings().all()
    return {'items':[{**dict(r),'review_overdue':r['released_at'] is None and r['review_at']<now()} for r in rows]}

@router.post('/press/staff/privacy/holds')
def add_hold(payload:HoldCreate,
             context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_rights import hold
    with db.begin():return hold(db,context[0],payload)

class HoldRelease(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:int=Field(ge=1)
    evidence_ref:str=Field(pattern=r'^[A-Za-z0-9_-]{8,120}$')

@router.post('/press/staff/privacy/holds/{ident}/release')
def release_hold(ident:UUID,payload:HoldRelease,context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_rights import release_hold
    with db.begin():return release_hold(db,context[0],ident,payload.expected_version,payload.evidence_ref)

@router.get('/press/staff/privacy/retention')
def retention_preview(context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_privacy import retention_preview
    return retention_preview(db,context[0])

@router.post('/press/staff/privacy/retention/run')
def retention_run(context=Depends(privacy_staff),db:Session=Depends(session)):
    from .media09_privacy import run_retention
    with db.begin():return run_retention(db,context[0])

class FollowUp(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    expected_version:int=Field(ge=1)
    note:str=Field(default='',max_length=500)
    follow_up_at:datetime | None=None
    substantive_correspondence_at:datetime | None=None
    disposition:str=Field(default='routine',pattern='^(routine|spam|invalid|relationship)$')
    retention_reviewed:bool=False

@router.patch('/press/staff/inquiries/{ident}/follow-up')
def follow_up(ident:UUID,payload:FollowUp,context=Depends(staff),db:Session=Depends(session)):
    from . import media09_privacy as privacy
    try:
        if payload.note:press._safe_text(payload.note)
    except ValueError:raise HTTPException(422,'Plain follow-up note required') from None
    for value in (payload.follow_up_at,payload.substantive_correspondence_at):
        if value and value.tzinfo is None:raise HTTPException(422,'Timezone-aware follow-up timestamp required')
    if payload.substantive_correspondence_at and payload.substantive_correspondence_at>privacy.now():
        raise HTTPException(422,'Correspondence cannot be in the future')
    org=context[0]
    with db.begin():
        press._advisory_lock(db,org);privacy.assert_record(db,org,'inquiries',ident)
        row=db.execute(select(details).where(details.c.id==ident,details.c.organization_id==org)).mappings().first()
        if not row:raise HTTPException(404,'Inquiry not found')
        if row['version']!=payload.expected_version:raise HTTPException(409,'Stale inquiry revision')
        if payload.substantive_correspondence_at and payload.substantive_correspondence_at<row['last_substantive_at']:
            raise HTTPException(409,'Correspondence history cannot move backwards')
        values={'follow_up_at':payload.follow_up_at,'follow_up_note':payload.note,'disposition':payload.disposition,
                'updated_at':privacy.now(),'version':row['version']+1}
        if payload.substantive_correspondence_at:values['last_substantive_at']=payload.substantive_correspondence_at
        if payload.retention_reviewed:values['retention_reviewed_at']=privacy.now()
        db.execute(update(details).where(details.c.id==ident,details.c.organization_id==org).values(**values))
        db.execute(insert(audit_events).values(organization_id=org,record_type='press_inquiries',record_id=ident,
            operation='updated',recorded_at=privacy.now()))
    return {'saved':True,'version':values['version']}

@router.get('/press/staff/privacy/status')
def privacy_status(context=Depends(privacy_staff),db:Session=Depends(session)):
    from . import media09_privacy as privacy
    privacy.guard(db,context[0])
    return {'retention_enabled':privacy.policy().enabled,'retention_approved':bool(privacy.policy().approval_ref),
        'real_erasure_enabled':os.getenv('SCEC_MEDIA09_REAL_ERASURE_ENABLED')=='1',
        'hubspot_connected':os.getenv('SCEC_MEDIA09_HUBSPOT_ENABLED')=='1',
        'rights_delivery':'manual_evidence_tracking','privacy_notice_acknowledgment_is_marketing_consent':False}

@router.get('/press/staff/hubspot/status')
def hubspot_status(context=Depends(staff)):
    from .hubspot import SCOPES
    enabled=os.getenv('SCEC_MEDIA09_HUBSPOT_ENABLED')=='1'
    path=Path(os.getenv('SCEC_HUBSPOT_TOKEN_FILE',''))
    safe=path.is_absolute() and path.is_file() and not path.is_symlink() and not path.stat().st_mode & 0o077
    approved=bool(os.getenv('SCEC_MEDIA09_HUBSPOT_PRIVACY_APPROVAL_REF'))
    return {'status':'disconnected' if not enabled else 'approval_required' if not approved else 'configured' if safe else 'credential_unavailable',
        'configured':enabled and safe and approved,'live_connection_verified':False,'scopes':list(SCOPES),
        'newsletter_sync':False,'private_research_sync':False}

class CompanySync(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    approved:bool
    domain:str=Field(min_length=4,max_length=253,pattern=r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')

@router.post('/press/staff/hubspot/company')
def sync_company(payload:CompanySync,context=Depends(staff),db:Session=Depends(session)):
    if 'administrator' not in context[2] or not payload.approved:raise HTTPException(403,'Explicit company export approval required')
    status=hubspot_status(context)
    if not status['configured']:raise HTTPException(503,'Optional HubSpot connector is not approved and configured')
    from .persistence.media09_privacy import company_syncs
    from . import media09_privacy as privacy
    from .persistence.models import TABLES
    org=context[0]
    with db.begin():
        privacy.guard(db,org);press._advisory_lock(db,org)
        organization=db.execute(select(TABLES['organizations'].c.payload).where(TABLES['organizations'].c.id==org)).scalar_one_or_none()
        if not organization:raise HTTPException(404,'Canonical organization not found')
        # Export only the current tenant's canonical organization name and the
        # explicitly reviewed domain. No arbitrary company/name payload proxy.
        connector=HubSpot(Path(os.environ['SCEC_HUBSPOT_TOKEN_FILE']).read_text().strip())
        try:result=connector.sync('companies',{'domain':payload.domain,'name':organization['name']},approved=True)
        finally:connector.close()
        outcome={**asdict(result),'at':datetime.now(timezone.utc).isoformat()}
        db.execute(privacy.pg_insert(company_syncs).values(organization_id=org,outcome=outcome,updated_at=privacy.now()).on_conflict_do_update(
            index_elements=[company_syncs.c.organization_id],set_={'outcome':outcome,'updated_at':privacy.now()}))
    return outcome
