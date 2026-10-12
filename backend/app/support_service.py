"""v8.4 support workflows; authenticated internal service only, no legacy system writes."""
from datetime import datetime, timezone
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from sqlalchemy import select, insert, update, and_, Table, Column, String, DateTime, ForeignKey, MetaData
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import IntegrityError
from app.contact_service import serialize
from app.contracts.canonical import Case
from app.persistence.models import TABLES
from app.persistence.audit import audit_events

metadata=MetaData()
support_history=Table('support_history', metadata,
    Column('id',PGUUID(as_uuid=True),primary_key=True),
    Column('organization_id',PGUUID(as_uuid=True),nullable=False),
    Column('case_id',PGUUID(as_uuid=True),nullable=False),
    Column('event_type',String(40),nullable=False),
    Column('from_status',String(30)),Column('to_status',String(30),nullable=False),
    Column('actor_ref',String(120),nullable=False),
    Column('note',String(2000)),Column('occurred_at',DateTime(timezone=True),nullable=False))

TRANSITIONS={
 'open':{'triaged','closed'},
 'triaged':{'in_progress','resolved','closed'},
 'in_progress':{'triaged','resolved'},
 'resolved':{'in_progress','closed'},
 'closed':set(),
}

class CaseTransition(BaseModel):
 model_config=ConfigDict(extra='forbid')
 status: Literal['open','triaged','in_progress','resolved','closed']
 actor_ref: str=Field(min_length=1,max_length=120)
 note: str|None=Field(default=None,max_length=2000)

class SupportFeedback(BaseModel):
 model_config=ConfigDict(extra='forbid')
 actor_ref: str=Field(min_length=1,max_length=120)
 note: str=Field(min_length=1,max_length=2000)


def _lookup_case(db, tenant, case_id, lock=False):
 q=select(TABLES['cases'].c.payload).where(and_(TABLES['cases'].c.id==case_id, TABLES['cases'].c.organization_id==tenant))
 if lock:q=q.with_for_update()
 return db.execute(q).scalar_one_or_none()

def _has_contact(db, tenant, contact_id):
 return bool(db.execute(select(TABLES['contacts'].c.id).where(and_(TABLES['contacts'].c.id==contact_id,TABLES['contacts'].c.organization_id==tenant))).first())

def create_case(payload: dict, tenant: UUID, db):
 model=Case.model_validate(payload)
 obj=serialize(model,tenant)
 if model.classification.value == 'public':
  raise HTTPException(422,'Support cases must not be public')
 if model.status!='open':
  raise HTTPException(422,'Cases must begin open; transition status through workflow')
 legacy=model.legacy_identity
 row=dict(id=model.id,organization_id=tenant,schema_version=model.schema_version,classification=model.classification.value,
  created_at=model.created_at,updated_at=model.updated_at,
  legacy_system=legacy.system.value if legacy else None,
  legacy_object_type=legacy.object_type if legacy else None,
  legacy_external_id=legacy.external_id if legacy else None,payload=obj)
 try:
  with db.begin():
   if not db.execute(select(TABLES['organizations'].c.id).where(TABLES['organizations'].c.id==tenant)).first():
    raise HTTPException(422,'Organization must be registered first')
   if model.requester_contact_id and not _has_contact(db,tenant,model.requester_contact_id):
    raise HTTPException(422,'Requester must be in the same organization')
   db.execute(insert(TABLES['cases']).values(**row))
   db.execute(insert(support_history).values(organization_id=tenant,case_id=model.id,event_type='created',from_status=None,to_status='open',actor_ref='system:service',occurred_at=datetime.now(timezone.utc)))
   db.execute(insert(audit_events).values(organization_id=tenant,record_type='cases',record_id=model.id,operation='created',recorded_at=datetime.now(timezone.utc)))
  return obj
 except IntegrityError:
  db.rollback()
  raise HTTPException(409,'Duplicate case or legacy identity')

def transition_case(tenant: UUID, case_id: UUID, change: CaseTransition, db):
 with db.begin():
  obj=_lookup_case(db,tenant,case_id,lock=True)
  if obj is None:raise HTTPException(404,'Case not found')
  before=obj['status']
  if change.status not in TRANSITIONS[before]:
   raise HTTPException(409,f'Invalid transition: {before} -> {change.status}')
  now=datetime.now(timezone.utc)
  new_obj={**obj,'status':change.status,'updated_at':now.isoformat()}
  db.execute(update(TABLES['cases']).where(and_(TABLES['cases'].c.id==case_id,TABLES['cases'].c.organization_id==tenant)).values(payload=new_obj,updated_at=now))
  db.execute(insert(support_history).values(organization_id=tenant,case_id=case_id,event_type='transition',from_status=before,to_status=change.status,actor_ref=change.actor_ref,note=change.note,occurred_at=now))
  db.execute(insert(audit_events).values(organization_id=tenant,record_type='cases',record_id=case_id,operation='updated',recorded_at=now))
 return new_obj

def add_feedback(tenant: UUID, case_id: UUID, payload: SupportFeedback, db):
 with db.begin():
  obj=_lookup_case(db,tenant,case_id,lock=True)
  if obj is None:raise HTTPException(404,'Case not found')
  now=datetime.now(timezone.utc)
  db.execute(insert(support_history).values(organization_id=tenant,case_id=case_id,event_type='feedback',from_status=obj['status'],to_status=obj['status'],actor_ref=payload.actor_ref,note=payload.note,occurred_at=now))
 return {'recorded':True,'case_id':str(case_id)}

def case_history(tenant: UUID, case_id: UUID, db, limit=50):
 if not 1<=limit<=100:raise HTTPException(422,'Limit must be between 1 and 100')
 if _lookup_case(db,tenant,case_id) is None:raise HTTPException(404,'Case not found')
 rows=db.execute(select(support_history).where(and_(support_history.c.organization_id==tenant,support_history.c.case_id==case_id)).order_by(support_history.c.occurred_at,support_history.c.id).limit(limit)).mappings().all()
 return {'items':[{k:(str(v) if isinstance(v,UUID) else v.isoformat() if isinstance(v,datetime) else v) for k,v in r.items()} for r in rows]}
