"""Privacy operations on the existing Media records. All destructive work defaults off.
The signed suppression ledger is outside database backups; its HMAC identifiers
are restricted pseudonymous data, not claimed to be anonymous audit records.
"""
import calendar
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile
from uuid import UUID, uuid4
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, insert, update, delete, func, cast, String
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .persistence.models import TABLES
from .persistence.audit import audit_events
from .persistence.media09 import press_inquiry_details as details
from .persistence.media09_privacy import (rights_requests,legal_holds,restrictions,
    attachments,privacy_state,deletion_receipts,backups)


def now():return datetime.now(timezone.utc)

def months(value, count):
    year,month=divmod(value.year*12+value.month-1+count,12)
    return value.replace(year=year,month=month+1,day=min(value.day,calendar.monthrange(year,month+1)[1]))

class RetentionPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid')
    enabled:bool=False
    version:str='OWNER-PROPOSED-NOT-APPROVED'
    approval_ref:str | None=None
    spam_days:int=Field(30,ge=1,le=365)
    closed_months:int=Field(12,ge=1,le=120)
    inactive_review_months:int=Field(6,ge=1,le=24)
    relationship_months:int=Field(24,ge=1,le=120)
    relationship_review_months:int=Field(12,ge=1,le=24)
    backup_days:int=Field(90,ge=1,le=365)
    security_log_days:int=Field(30,ge=30,le=90)
    receipt_months:int=Field(24,ge=1,le=120)


def policy():
    path=os.getenv('SCEC_MEDIA09_RETENTION_POLICY_FILE')
    if not path:return RetentionPolicy()
    return RetentionPolicy.model_validate_json(protected_file(path).read_text())


def protected_file(value):
    p=Path(value)
    if not p.is_absolute() or p.is_symlink() or not p.is_file() or p.stat().st_mode & 0o077:
        raise HTTPException(503,'Protected privacy file required')
    return p


def enabled():
    if os.getenv('SCEC_MEDIA09_PRIVACY_ENABLED')!='1':
        raise HTTPException(503,'Privacy operations disabled')
    ledger_path();key()


def key():
    raw=protected_file(os.getenv('SCEC_MEDIA09_PRIVACY_KEY_FILE','')).read_bytes().strip()
    if len(raw)<32:raise HTTPException(503,'Privacy key unavailable')
    return raw


def ledger_path():
    p=Path(os.getenv('SCEC_MEDIA09_SUPPRESSION_FILE',''))
    if not p.is_absolute() or p.is_symlink() or not p.parent.is_dir() or p.parent.stat().st_mode & 0o077:
        raise HTTPException(503,'Private suppression directory required')
    if p.exists():protected_file(str(p))
    return p


def digest(tenant,kind,ident):
    return hmac.new(key(),f'media09:erase:v1:{tenant}:{kind}:{ident}'.encode(),hashlib.sha256).hexdigest()


def sign(value):
    return hmac.new(key(),b'media09:ledger:v1:'+json.dumps(value,sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()

@contextmanager
def ledger():
    path=ledger_path()
    lock=path.with_suffix('.lock')
    if lock.is_symlink():raise HTTPException(503,'Invalid suppression lock')
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'r+') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        if not path.exists():
            raise HTTPException(503,'Suppression ledger missing; initialize only for a new fixture or approved baseline')
        try:
            wrapped=json.loads(path.read_text())
            value=wrapped['ledger']
            if not hmac.compare_digest(wrapped['signature'],sign(value)) or value.get('version')!=1 or not isinstance(value.get('tenants'),dict):
                raise ValueError()
        except (ValueError,KeyError,TypeError):
            raise HTTPException(503,'Suppression ledger integrity failure') from None
        yield value


def save_ledger(value):
    path=ledger_path()
    payload=json.dumps({'ledger':value,'signature':sign(value)},sort_keys=True)
    fd,name=tempfile.mkstemp(prefix='.media09-ledger-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
        directory=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)


def initialize_ledger():
    enabled()
    path=ledger_path()
    # Never silently replace a missing ledger on an existing deployment.
    if path.exists():raise HTTPException(409,'Suppression ledger already exists')
    if os.getenv('SCEC_MEDIA09_NEW_SYNTHETIC_BASELINE')!='1' or os.getenv('SCEC_ENV')=='production':
        raise HTTPException(503,'Explicit new synthetic baseline required')
    save_ledger({'version':1,'tenants':{}})


def configured():return os.getenv('SCEC_MEDIA09_PRIVACY_ENABLED')=='1' or bool(os.getenv('SCEC_MEDIA09_SUPPRESSION_FILE'))

def generation(db,tenant):
    return db.execute(select(privacy_state.c.generation).where(privacy_state.c.organization_id==tenant)).scalar_one_or_none() or 0


def set_generation(db,tenant,value):
    db.execute(pg_insert(privacy_state).values(organization_id=tenant,generation=value).on_conflict_do_update(
        index_elements=[privacy_state.c.organization_id],set_={'generation':value}))


def guard(db,tenant):
    if not configured():return
    with ledger() as value:
        expected=value['tenants'].get(str(tenant),{}).get('generation',0)
        if generation(db,tenant)!=expected:
            raise HTTPException(503,'Privacy reconciliation required before serving restored data')


def suppressed(tenant,kind,ident):
    if not configured():return False
    with ledger() as value:
        token=digest(tenant,kind,ident)
        return any(token in e['targets'].get(kind,[]) for e in value['tenants'].get(str(tenant),{}).get('entries',[]))


def assert_record(db,tenant,kind,ident):
    if not configured():return
    guard(db,tenant)
    if suppressed(tenant,kind,ident):raise HTTPException(410,'Record erased')
    if kind=='contacts':
        blocked=db.execute(select(restrictions.c.contact_id).where(restrictions.c.organization_id==tenant,
            restrictions.c.contact_id==ident,restrictions.c.active==True)).first()
        if blocked:raise HTTPException(423,'Processing restricted pending privacy review')
    if kind=='inquiries':
        row=db.execute(select(TABLES['inquiries'].c.payload).where(TABLES['inquiries'].c.organization_id==tenant,TABLES['inquiries'].c.id==ident)).scalar_one_or_none()
        if row and row.get('contact_id'):assert_record(db,tenant,'contacts',UUID(row['contact_id']))


def lock(db,tenant):
    from .media09_press import _advisory_lock
    _advisory_lock(db,tenant)


def owned_path(root_env,object_key):
    root=Path(os.getenv(root_env,''))
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
        raise HTTPException(503,'Protected Media storage mount required')
    parts=object_key.split('/')
    if any(not part or part in ('.','..') for part in parts):raise HTTPException(409,'Invalid managed object key')
    target=root.joinpath(*parts)
    for parent in [target,*target.parents]:
        if parent==root:break
        if parent.is_symlink():raise HTTPException(409,'Symlinked managed object refused')
    if not target.resolve().is_relative_to(root.resolve()):raise HTTPException(409,'Object outside Media storage')
    if target.exists() and (not target.is_file() or target.stat().st_nlink!=1):raise HTTPException(409,'Unsafe managed object')
    return target


def attachment_path(tenant,inquiry,ident,object_key):
    if object_key!=f'{tenant}/{inquiry}/{ident}':raise HTTPException(409,'Attachment ownership mismatch')
    return owned_path('SCEC_MEDIA09_ATTACHMENT_ROOT',object_key)


def _record_receipt(db,tenant,reason,counts,ident=None,at=None):
    ident=ident or uuid4()
    db.execute(pg_insert(deletion_receipts).values(id=ident,organization_id=tenant,reason=reason,
        counts=counts,recorded_at=at or now()).on_conflict_do_nothing())
    return ident


def _rights_redact(db,tenant,ids,receipt):
    if ids:db.execute(update(rights_requests).where(rights_requests.c.organization_id==tenant,rights_requests.c.id.in_(ids)).values(
        requester_email=None,contact_id=None,verification_ref=None,response_ref=None,extension_ref=None,erasure_receipt=receipt))


def erase(db,tenant,contact_id,*,reason='rights',inquiry_ids=None,synthetic_external=False):
    """Called in a caller-owned transaction. No blanket cross-product deletion."""
    enabled();guard(db,tenant);lock(db,tenant)
    contact=db.execute(select(TABLES['contacts'].c.payload).where(TABLES['contacts'].c.id==contact_id,TABLES['contacts'].c.organization_id==tenant)).scalar_one_or_none()
    if contact is None:raise HTTPException(404,'Contact not found')
    if db.execute(select(legal_holds.c.id).where(legal_holds.c.organization_id==tenant,legal_holds.c.contact_id==contact_id,legal_holds.c.released_at.is_(None))).first():
        raise HTTPException(423,'Legal hold requires authorized release, including overdue holds')
    rows=db.execute(select(details).where(details.c.organization_id==tenant,details.c.contact_id==contact_id)).mappings().all()
    selected=[r for r in rows if inquiry_ids is None or r['id'] in inquiry_ids]
    if not selected:raise HTTPException(404,'Media inquiry not found')
    synthetic=all(r['synthetic_only'] for r in selected)
    if not synthetic:
        from .media09_release import approved_notice
        approved_notice()
        if os.getenv('SCEC_MEDIA09_REAL_ERASURE_ENABLED')!='1' or not policy().approval_ref:
            raise HTTPException(503,'Real erasure requires separately approved policy and operation')
    ids=[r['id'] for r in selected]
    # External records cannot be silently forgotten after a local deletion.
    if any(r['sync_result'] and r['sync_result'].get('state')=='synced' for r in selected) and not (synthetic and synthetic_external):
        raise HTTPException(409,'External CRM erasure must be reconciled before local completion')
    all_inquiries=db.execute(select(TABLES['inquiries'].c.id).where(TABLES['inquiries'].c.organization_id==tenant,
        TABLES['inquiries'].c.payload['contact_id'].astext==str(contact_id))).scalars().all()
    shared=[]
    for name,table in TABLES.items():
        if name in ('organizations','contacts','inquiries'):continue
        if db.execute(select(table.c.id).where(table.c.organization_id==tenant,cast(table.c.payload,String).contains(str(contact_id))).limit(1)).first():shared.append(name)
    delete_contact=not shared and set(all_inquiries)<=set(ids)
    if inquiry_ids is None and not delete_contact:
        raise HTTPException(409,'Shared canonical records require their owning workflow review; erasure not completed')
    files=db.execute(select(attachments).where(attachments.c.organization_id==tenant,attachments.c.inquiry_id.in_(ids))).mappings().all()
    paths=[attachment_path(tenant,r['inquiry_id'],r['id'],r['object_key']) for r in files]
    rights_ids=db.execute(select(rights_requests.c.id).where(rights_requests.c.organization_id==tenant,rights_requests.c.contact_id==contact_id)).scalars().all() if delete_contact else []
    targets={'inquiries':[digest(tenant,'inquiries',i) for i in ids],
             'contacts':[digest(tenant,'contacts',contact_id)] if delete_contact else [],
             'attachments':[digest(tenant,'attachments',r['object_key']) for r in files],
             'rights':[digest(tenant,'rights',i) for i in rights_ids]}
    receipt=uuid4();at=now()
    counts={'inquiries':len(ids),'contacts':int(delete_contact),'attachments':len(files),'rights_redacted':len(rights_ids)}
    # Durably suppress before any irreversible file or database deletion. If
    # this transaction fails, generation mismatch blocks service until repair.
    with ledger() as value:
        state=value['tenants'].setdefault(str(tenant),{'generation':0,'entries':[]})
        state['generation']+=1
        state['entries'].append({'generation':state['generation'],'receipt':str(receipt),'at':at.isoformat(),'reason':reason,'targets':targets,'counts':counts})
        save_ledger(value)
        new_generation=state['generation']
    for path in paths:path.unlink(missing_ok=True)
    _delete_rows(db,tenant,ids,[contact_id] if delete_contact else [],rights_ids,receipt)
    set_generation(db,tenant,new_generation)
    _record_receipt(db,tenant,reason,counts,receipt,at)
    return {'receipt_id':str(receipt),'counts':counts,'contact_retained_for_other_purpose':not delete_contact}


def _delete_rows(db,tenant,ids,contacts,rights_ids,receipt):
    db.execute(delete(attachments).where(attachments.c.organization_id==tenant,attachments.c.inquiry_id.in_(ids)))
    db.execute(delete(details).where(details.c.organization_id==tenant,details.c.id.in_(ids)))
    db.execute(delete(TABLES['inquiries']).where(TABLES['inquiries'].c.organization_id==tenant,TABLES['inquiries'].c.id.in_(ids)))
    # Remove old UUID-linked audit events as part of erasure. The replacement
    # receipt contains counts/reason/time, without record or actor identifiers.
    db.execute(delete(audit_events).where(audit_events.c.organization_id==tenant,audit_events.c.record_id.in_(ids+contacts)))
    if contacts:
        db.execute(delete(restrictions).where(restrictions.c.organization_id==tenant,restrictions.c.contact_id.in_(contacts)))
        db.execute(delete(legal_holds).where(legal_holds.c.organization_id==tenant,legal_holds.c.contact_id.in_(contacts)))
        db.execute(delete(TABLES['contacts']).where(TABLES['contacts'].c.organization_id==tenant,TABLES['contacts'].c.id.in_(contacts)))
    _rights_redact(db,tenant,rights_ids,receipt)


def apply_suppression(db,tenant):
    """Only signed prior deletion decisions, before a restored DB serves traffic."""
    enabled();lock(db,tenant)
    with ledger() as value:
        state=value['tenants'].get(str(tenant),{'generation':0,'entries':[]})
        if generation(db,tenant)<state.get('minimum_generation',0):
            raise HTTPException(503,'Restored backup is older than the supported suppression window')
        for entry in state['entries']:
            target=entry['targets']
            ids={name:[i for i in db.execute(select(TABLES[name].c.id).where(TABLES[name].c.organization_id==tenant)).scalars()
                       if digest(tenant,name,i) in target.get(name,[])] for name in ('contacts','inquiries')}
            rows=db.execute(select(attachments).where(attachments.c.organization_id==tenant)).mappings().all()
            for row in rows:
                if digest(tenant,'attachments',row['object_key']) in target.get('attachments',[]):
                    attachment_path(tenant,row['inquiry_id'],row['id'],row['object_key']).unlink(missing_ok=True)
            rights_ids=[i for i in db.execute(select(rights_requests.c.id).where(rights_requests.c.organization_id==tenant)).scalars()
                        if digest(tenant,'rights',i) in target.get('rights',[])]
            receipt=UUID(entry['receipt'])
            _delete_rows(db,tenant,ids['inquiries'],ids['contacts'],rights_ids,receipt)
            _record_receipt(db,tenant,entry['reason'],entry['counts'],receipt,datetime.fromisoformat(entry['at']))
        set_generation(db,tenant,state['generation'])
    return {'suppression_applied':True,'generation':state['generation']}


def retention_preview(db,tenant,at=None,p=None):
    p=p or policy();at=at or now();guard(db,tenant)
    items=[]
    for row in db.execute(select(details).where(details.c.organization_id==tenant)).mappings():
        activity=row['last_substantive_at']
        held=db.execute(select(legal_holds.c.id).where(legal_holds.c.organization_id==tenant,legal_holds.c.contact_id==row['contact_id'],legal_holds.c.released_at.is_(None))).first() is not None
        action=None
        if row['disposition'] in ('spam','invalid') and activity+timedelta(days=p.spam_days)<=at:action='erase'
        elif row['disposition']=='relationship':
            if months(activity,p.relationship_months)<=at:action='erase'
            elif months(row['retention_reviewed_at'] or activity,p.relationship_review_months)<=at:action='review'
        elif row['status']=='closed' and months(activity,p.closed_months)<=at:action='erase'
        elif row['status']!='closed' and months(row['retention_reviewed_at'] or activity,p.inactive_review_months)<=at:action='review'
        if action and row['retention_exception_ref'] and row['retention_exception_until'] and row['retention_exception_until']>at:
            action='retained_exception'
        if action:items.append({'inquiry_id':str(row['id']),'contact_id':str(row['contact_id']),'action':'held' if held else action,'synthetic_only':row['synthetic_only']})
    return {'policy_enabled':p.enabled,'policy_version':p.version,'items':items}


def run_retention(db,tenant,*,at=None,synthetic_external=False):
    enabled();p=policy()
    if not p.enabled:raise HTTPException(503,'Retention policy defaults disabled')
    lock(db,tenant)
    candidates=retention_preview(db,tenant,at,p)
    grouped={}
    for item in candidates['items']:
        if item['action']=='erase':grouped.setdefault(UUID(item['contact_id']),[]).append(UUID(item['inquiry_id']))
    receipts=[]
    for contact,ids in grouped.items():
        receipts.append(erase(db,tenant,contact,reason='retention',inquiry_ids=ids,synthetic_external=synthetic_external))
    cutoff=months(at or now(),-p.receipt_months)
    db.execute(delete(deletion_receipts).where(deletion_receipts.c.organization_id==tenant,deletion_receipts.c.recorded_at<cutoff))
    # Rights history is restricted operational correspondence, not an anonymous
    # receipt. Closed history uses the configured closed-record retention.
    rights_cutoff=months(at or now(),-p.closed_months)
    closed=db.execute(select(rights_requests.c.id,rights_requests.c.contact_id,rights_requests.c.synthetic_only).where(rights_requests.c.organization_id==tenant,
        rights_requests.c.closed_at<rights_cutoff,rights_requests.c.requester_email.is_not(None))).all()
    for rid,cid,synthetic in closed:
        permit_real(synthetic)
        if cid and db.execute(select(legal_holds.c.id).where(legal_holds.c.organization_id==tenant,legal_holds.c.contact_id==cid,legal_holds.c.released_at.is_(None))).first():continue
        # Closed rights entries are scrubbed rather than silently resurrected by
        # old backups; the same external ledger must cover their deletion.
        _redact_closed_right(db,tenant,rid)
    return {'receipts':receipts,'review_count':sum(i['action']=='review' for i in candidates['items']),'held_count':sum(i['action']=='held' for i in candidates['items'])}


def _redact_closed_right(db,tenant,rid):
    with ledger() as value:
        state=value['tenants'].setdefault(str(tenant),{'generation':0,'entries':[]});state['generation']+=1
        receipt=uuid4()
        state['entries'].append({'generation':state['generation'],'receipt':str(receipt),'at':now().isoformat(),'reason':'rights_retention',
            'targets':{'rights':[digest(tenant,'rights',rid)]},'counts':{'rights_redacted':1}})
        save_ledger(value);new_generation=state['generation']
    _rights_redact(db,tenant,[rid],receipt);set_generation(db,tenant,new_generation)
    _record_receipt(db,tenant,'rights_retention',{'rights_redacted':1},receipt)


def permit_real(synthetic):
    if synthetic:return
    from .media09_release import approved_notice
    approved_notice()
    if os.getenv('SCEC_MEDIA09_REAL_ERASURE_ENABLED')!='1' or not policy().approval_ref:
        raise HTTPException(503,'Real privacy mutation requires approved policy and operation')


def register_backup(db,tenant,ident,*,synthetic_only,created_at=None):
    enabled();guard(db,tenant);permit_real(synthetic_only)
    created_at=created_at or now();p=policy()
    if not p.enabled:raise HTTPException(503,'Backup policy disabled')
    object_key=f'{ident}.dump'
    path=owned_path('SCEC_MEDIA09_BACKUP_ROOT',object_key)
    if not path.is_file():raise HTTPException(404,'Managed backup not found')
    data={'id':str(ident),'organization_id':str(tenant),'object_key':object_key,
          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'generation':generation(db,tenant),
          'created_at':created_at.isoformat(),'expires_at':(created_at+timedelta(days=p.backup_days)).isoformat(),
          'synthetic_only':synthetic_only,'expired_at':None}
    sidecar=path.with_suffix('.json')
    if sidecar.exists():raise HTTPException(409,'Backup already registered')
    fd=os.open(sidecar,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:
        f.write(json.dumps({'backup':data,'signature':sign(data)}));f.flush();os.fsync(f.fileno())
    db.execute(insert(backups).values(id=ident,organization_id=tenant,object_key=object_key,
        sha256=data['sha256'],generation=data['generation'],created_at=created_at,expires_at=created_at+timedelta(days=p.backup_days)))
    return {'backup_id':str(ident),'expires_at':data['expires_at']}


def backup_manifest(ident):
    path=owned_path('SCEC_MEDIA09_BACKUP_ROOT',f'{ident}.json')
    try:
        wrapped=json.loads(protected_file(str(path)).read_text());value=wrapped['backup']
        if not hmac.compare_digest(wrapped['signature'],sign(value)) or value['id']!=str(ident):raise ValueError()
        return value
    except (ValueError,KeyError,TypeError):raise HTTPException(503,'Backup inventory integrity failure') from None


def assert_backup_restorable(ident,at=None):
    value=backup_manifest(ident)
    if value['expired_at'] or datetime.fromisoformat(value['expires_at'])<=(at or now()):
        raise HTTPException(410,'Backup expired; restore refused')
    path=owned_path('SCEC_MEDIA09_BACKUP_ROOT',value['object_key'])
    if not path.exists() or not hmac.compare_digest(hashlib.sha256(path.read_bytes()).hexdigest(),value['sha256']):
        raise HTTPException(503,'Backup content unavailable or changed')
    return value


def expire_backups(db,tenant,at=None):
    enabled();p=policy();at=at or now();guard(db,tenant);lock(db,tenant)
    if not p.enabled:raise HTTPException(503,'Backup expiration defaults disabled')
    # A full DB dump can contain multiple tenants. Conservatively retain it
    # while ANY unreleased legal hold exists, even an overdue review.
    if db.execute(select(legal_holds.c.id).where(legal_holds.c.released_at.is_(None))).first():
        return {'expired':0,'held':True}
    count=0
    for row in db.execute(select(backups).where(backups.c.organization_id==tenant,backups.c.expires_at<=at)).mappings():
        value=backup_manifest(row['id']);permit_real(value['synthetic_only'])
        path=owned_path('SCEC_MEDIA09_BACKUP_ROOT',row['object_key'])
        if row['expired_at'] is not None and not path.exists():continue
        path.unlink(missing_ok=True)
        value['expired_at']=at.isoformat()
        # Expiration sidecar survives restoration of an older inventory table.
        sidecar=path.with_suffix('.json');fd,name=tempfile.mkstemp(dir=sidecar.parent,prefix='.backup-')
        with os.fdopen(fd,'w') as f:
            f.write(json.dumps({'backup':value,'signature':sign(value)}));f.flush();os.fsync(f.fileno())
        os.replace(name,sidecar)
        db.execute(update(backups).where(backups.c.id==row['id'],backups.c.organization_id==tenant).values(expired_at=at));count+=1
    if count:_record_receipt(db,tenant,'backup_expiration',{'backups':count},at=at)
    return {'expired':count,'held':False}


def expire_logs(db,tenant,*,synthetic_only=False,at=None):
    """Only the explicitly mounted Media-owned log directory, never host journals."""
    enabled();guard(db,tenant);lock(db,tenant);permit_real(synthetic_only)
    p=policy();at=at or now()
    if not p.enabled:raise HTTPException(503,'Log retention defaults disabled')
    root=Path(os.getenv('SCEC_MEDIA09_LOG_ROOT',''))
    # Validate the same protected storage boundary even if the directory is empty.
    owned_path('SCEC_MEDIA09_LOG_ROOT','validation-placeholder')
    if db.execute(select(legal_holds.c.id).where(legal_holds.c.released_at.is_(None))).first():return {'expired':0,'held':True}
    count=0
    for candidate in root.iterdir():
        import re
        if not re.fullmatch(r'media09-\d{8}\.log',candidate.name):continue
        path=owned_path('SCEC_MEDIA09_LOG_ROOT',candidate.name)
        if datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)+timedelta(days=p.security_log_days)<=at:
            path.unlink();count+=1
    if count:_record_receipt(db,tenant,'log_expiration',{'logs':count},at=at)
    return {'expired':count,'held':False}


def compact_suppression(db,tenant,at=None):
    """Minimize pseudonymous markers only after approved complete backup coverage.
    Restores older than the retained suppression window are permanently refused.
    """
    enabled();guard(db,tenant);lock(db,tenant);p=policy();at=at or now()
    if not p.enabled or not p.approval_ref or not os.getenv('SCEC_MEDIA09_BACKUP_COVERAGE_APPROVAL_REF'):
        raise HTTPException(503,'Approved policy and complete backup inventory required for compaction')
    root=Path(os.getenv('SCEC_MEDIA09_BACKUP_ROOT',''))
    owned_path('SCEC_MEDIA09_BACKUP_ROOT','validation-placeholder')
    active=[]
    for path in root.glob('*.dump'):
        try:ident=UUID(path.stem)
        except ValueError:raise HTTPException(409,'Unregistered backup blocks marker compaction') from None
        if not path.with_suffix('.json').exists():raise HTTPException(409,'Unregistered backup blocks marker compaction')
        value=backup_manifest(ident)
        if not value['expired_at']:active.append(value)
    with ledger() as value:
        state=value['tenants'].get(str(tenant),{'generation':0,'entries':[]})
        kept=[];floor=state.get('minimum_generation',0);removed=0
        for index,entry in enumerate(state['entries']):
            created=datetime.fromisoformat(entry['at'])
            if created+timedelta(days=p.backup_days)<=at and not any(datetime.fromisoformat(b['created_at'])<=created for b in active):
                floor=max(floor,entry.get('generation',index+1));removed+=1
            else:kept.append(entry)
        if removed:
            state['entries']=kept;state['minimum_generation']=floor;state['generation']+=1
            value['tenants'][str(tenant)]=state;save_ledger(value);set_generation(db,tenant,state['generation'])
    return {'markers_removed':removed,'minimum_restorable_generation':floor}
