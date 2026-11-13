"""Restricted, manually verified rights workflow. No identity-document uploads or email sending."""
from datetime import datetime,timedelta
import re
from uuid import UUID,uuid4
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field,field_validator
from sqlalchemy import select,insert,update,func
from . import media09_privacy as privacy
from .persistence.media09_privacy import rights_requests as rights,legal_holds,restrictions
from .persistence.models import TABLES

REF=re.compile(r'^[A-Za-z0-9_-]{8,120}$')

class RightsCreate(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    email:str=Field(max_length=254)
    kind:str=Field(pattern='^(access|rectify|erase|restrict|object|portability)$')
    privacy_notice_acknowledged:bool
    company:str=Field(default='',max_length=0)
    synthetic:bool=True
    @field_validator('email')
    @classmethod
    def email_valid(cls,value):
        from .media09_press import EMAIL_RE
        if not EMAIL_RE.fullmatch(value):raise ValueError('Invalid reply address')
        return value.casefold()
    @field_validator('privacy_notice_acknowledged')
    @classmethod
    def acknowledged(cls,value):
        if not value:raise ValueError('Notice acknowledgment required')
        return value

class RightsReview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:int=Field(ge=1)
    action:str=Field(pattern='^(verify|start|respond|close|extend|restrict|release_restriction|erase)$')
    evidence_ref:str=Field(pattern=r'^[A-Za-z0-9_-]{8,120}$')
    contact_id:UUID | None=None
    response_ref:str | None=Field(default=None,pattern=r'^[A-Za-z0-9_-]{8,120}$')


def create(db,tenant,payload):
    privacy.enabled();privacy.guard(db,tenant);privacy.lock(db,tenant)
    if payload.synthetic:
        from .media09_press import SYNTHETIC_DOMAINS
        if payload.email.rsplit('@',1)[-1] not in SYNTHETIC_DOMAINS:raise HTTPException(422,'Synthetic reserved email required')
    else:
        from .media09_release import approved_notice
        approved_notice()
    recent=db.execute(select(func.count()).select_from(rights).where(rights.c.organization_id==tenant,rights.c.received_at>=privacy.now()-timedelta(minutes=1))).scalar_one()
    if recent>=5:raise HTTPException(429,'Rights intake rate limit exceeded')
    # Repeat submissions do not reveal whether a contact exists or generate
    # unlimited copies. Identity is never inferred from an email match.
    previous=db.execute(select(rights.c.id).where(rights.c.organization_id==tenant,rights.c.requester_email==payload.email,
        rights.c.kind==payload.kind,rights.c.status.notin_(['responded','closed']))).scalar_one_or_none()
    if previous:return {'request_id':str(previous),'received':True,'identity_verified':False}
    ident=uuid4();at=privacy.now()
    db.execute(insert(rights).values(id=ident,organization_id=tenant,requester_email=payload.email,kind=payload.kind,
        synthetic_only=payload.synthetic,status='received',version=1,received_at=at,due_at=privacy.months(at,1)))
    return {'request_id':str(ident),'received':True,'identity_verified':False}


def review(db,tenant,ident,change):
    privacy.enabled();privacy.guard(db,tenant);privacy.lock(db,tenant)
    row=db.execute(select(rights).where(rights.c.id==ident,rights.c.organization_id==tenant).with_for_update()).mappings().first()
    if row is None:raise HTTPException(404,'Rights request not found')
    if row['version']!=change.expected_version:raise HTTPException(409,'Stale rights revision')
    privacy.permit_real(row['synthetic_only'])
    action=change.action;at=privacy.now();values={'version':row['version']+1}
    if action=='verify':
        if row['status']!='received' or not change.contact_id:raise HTTPException(409,'Received request and verified contact required')
        contact=db.execute(select(TABLES['contacts'].c.payload).where(TABLES['contacts'].c.organization_id==tenant,TABLES['contacts'].c.id==change.contact_id)).scalar_one_or_none()
        if not contact or (contact.get('email') or '').casefold()!=row['requester_email']:
            raise HTTPException(409,'Verified contact does not match request scope')
        # The opaque reference records independent proportional verification;
        # email equality alone is explicitly not a verification mechanism.
        values.update(contact_id=change.contact_id,verification_ref=change.evidence_ref,status='verified')
    elif action=='extend':
        if row['extension_ref'] or at>privacy.months(row['received_at'],1) or row['status'] in ('closed','responded'):
            raise HTTPException(409,'Extension must be justified and recorded within the initial deadline')
        values.update(extension_ref=change.evidence_ref,due_at=privacy.months(row['received_at'],3))
    elif action in ('respond','close'):
        if action=='respond':
            if not change.response_ref or row['status'] in ('closed','responded'):raise HTTPException(409,'Response evidence required')
            values.update(status='responded',responded_at=at,response_ref=change.response_ref)
        else:
            if row['status']!='responded':raise HTTPException(409,'Record a response before closing')
            values.update(status='closed',closed_at=at)
    else:
        if row['status'] not in ('verified','in_progress') or not row['verification_ref'] or not row['contact_id']:
            raise HTTPException(409,'Independent identity verification required')
        if action=='start':values['status']='in_progress'
        elif action in ('restrict','release_restriction'):
            db.execute(privacy.pg_insert(restrictions).values(contact_id=row['contact_id'],organization_id=tenant,
                active=action=='restrict',updated_at=at).on_conflict_do_update(index_elements=[restrictions.c.contact_id],
                set_={'active':action=='restrict','updated_at':at}))
            values['status']='in_progress'
        elif action=='erase':
            if row['kind']!='erase':raise HTTPException(409,'Erasure requires an erasure request')
            result=privacy.erase(db,tenant,row['contact_id'],reason='rights')
            values.update(erasure_receipt=UUID(result['receipt_id']),status='in_progress',contact_id=None,
                requester_email=None,verification_ref=None,response_ref=None,extension_ref=None)
    db.execute(update(rights).where(rights.c.id==ident,rights.c.organization_id==tenant).values(**values))
    return {'request_id':str(ident),'status':values.get('status',row['status']),'version':values['version'],
            'response_sent':False,'erasure_receipt':str(values['erasure_receipt']) if values.get('erasure_receipt') else None}


def queue(db,tenant,offset=0):
    privacy.enabled();privacy.guard(db,tenant)
    rows=db.execute(select(rights).where(rights.c.organization_id==tenant).order_by(rights.c.received_at,rights.c.id).limit(50).offset(offset)).mappings().all()
    return {'items':[{**dict(r),'overdue':r['responded_at'] is None and r['due_at']<privacy.now()} for r in rows]}

class HoldCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    contact_id:UUID
    reason:str=Field(pattern='^(legal_requirement|litigation|rights_preservation)$')
    case_ref:str=Field(pattern=r'^[A-Za-z0-9_-]{8,120}$')
    review_at:datetime


def hold(db,tenant,payload):
    privacy.enabled();privacy.guard(db,tenant);privacy.lock(db,tenant)
    if payload.review_at.tzinfo is None or payload.review_at<=privacy.now():raise HTTPException(422,'Future timezone-aware hold review required')
    if not db.execute(select(TABLES['contacts'].c.id).where(TABLES['contacts'].c.organization_id==tenant,TABLES['contacts'].c.id==payload.contact_id)).first():
        raise HTTPException(404,'Contact not found')
    ident=uuid4()
    db.execute(insert(legal_holds).values(id=ident,organization_id=tenant,contact_id=payload.contact_id,reason=payload.reason,
        case_ref=payload.case_ref,review_at=payload.review_at,created_at=privacy.now(),version=1))
    return {'hold_id':str(ident),'version':1}


def release_hold(db,tenant,ident,version,reference):
    privacy.enabled();privacy.guard(db,tenant);privacy.lock(db,tenant)
    if not REF.fullmatch(reference):raise HTTPException(422,'Opaque release reference required')
    row=db.execute(update(legal_holds).where(legal_holds.c.id==ident,legal_holds.c.organization_id==tenant,
        legal_holds.c.version==version,legal_holds.c.released_at.is_(None)).values(released_at=privacy.now(),release_ref=reference,version=version+1))
    if row.rowcount!=1:raise HTTPException(409,'Stale or unavailable hold')
    return {'released':True,'version':version+1}


def subject_data(db,tenant,ident):
    privacy.enabled();privacy.guard(db,tenant)
    row=db.execute(select(rights).where(rights.c.id==ident,rights.c.organization_id==tenant)).mappings().first()
    if not row:raise HTTPException(404,'Rights request not found')
    if row['status'] not in ('verified','in_progress') or not row['verification_ref'] or row['kind'] not in ('access','portability'):
        raise HTTPException(409,'Verified applicable access/portability review required')
    privacy.permit_real(row['synthetic_only'])
    cid=row['contact_id']
    contact=db.execute(select(TABLES['contacts'].c.payload).where(TABLES['contacts'].c.id==cid,TABLES['contacts'].c.organization_id==tenant)).scalar_one_or_none()
    rows=db.execute(select(privacy.details).where(privacy.details.c.contact_id==cid,privacy.details.c.organization_id==tenant)).mappings().all()
    inquiries=[]
    for item in rows:
        inquiry=db.execute(select(TABLES['inquiries'].c.payload).where(TABLES['inquiries'].c.id==item['id'],TABLES['inquiries'].c.organization_id==tenant)).scalar_one()
        inquiries.append({'id':item['id'],'subject':inquiry['subject'],'message':item['body'],'kind':item['kind'],
            'status':item['status'],'privacy_notice_version':item['notice_version']})
    return {'contact':contact,'inquiries':inquiries,'format':'json','automatically_delivered':False}

class Correction(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    expected_version:int=Field(ge=1)
    display_name:str=Field(min_length=3,max_length=120)
    email:str=Field(min_length=6,max_length=254)
    evidence_ref:str=Field(pattern=r'^[A-Za-z0-9_-]{8,120}$')


def correct(db,tenant,ident,payload):
    privacy.enabled();privacy.guard(db,tenant);privacy.lock(db,tenant)
    row=db.execute(select(rights).where(rights.c.id==ident,rights.c.organization_id==tenant)).mappings().first()
    if not row:raise HTTPException(404,'Rights request not found')
    if row['kind']!='rectify' or row['status'] not in ('verified','in_progress') or not row['verification_ref'] or row['version']!=payload.expected_version:
        raise HTTPException(409,'Verified current rectification request required')
    privacy.permit_real(row['synthetic_only'])
    from .media09_press import EMAIL_RE,SYNTHETIC_DOMAINS,_safe_text
    email=payload.email.casefold()
    if not EMAIL_RE.fullmatch(email):raise HTTPException(422,'Valid reply email required')
    try:_safe_text(payload.display_name)
    except ValueError:raise HTTPException(422,'Plain display name required') from None
    if row['synthetic_only'] and (not payload.display_name.startswith('Synthetic ') or email.rsplit('@',1)[-1] not in SYNTHETIC_DOMAINS):
        raise HTTPException(422,'Synthetic correction required')
    contact=db.execute(select(TABLES['contacts'].c.payload).where(TABLES['contacts'].c.id==row['contact_id'],TABLES['contacts'].c.organization_id==tenant)).scalar_one()
    value=dict(contact,display_name=payload.display_name,email=email,updated_at=privacy.now().isoformat())
    db.execute(update(TABLES['contacts']).where(TABLES['contacts'].c.id==row['contact_id'],TABLES['contacts'].c.organization_id==tenant).values(payload=value,updated_at=privacy.now()))
    db.execute(update(rights).where(rights.c.id==ident,rights.c.organization_id==tenant).values(status='in_progress',version=row['version']+1))
    return {'corrected':True,'version':row['version']+1}
