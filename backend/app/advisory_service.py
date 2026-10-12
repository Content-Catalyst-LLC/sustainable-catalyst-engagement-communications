"""v8.5 advisory workflows: tenant scoped, opt-in, approval gated, append-only lineage.
Approval actors are service-attested references, NOT independently verified user identities.
"""
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import MetaData, Table, Column, String, DateTime, ForeignKey, select, insert, update, and_
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import IntegrityError
from app.contracts.canonical import AdvisoryEngagement
from app.contact_service import serialize
from app.persistence.models import TABLES
from app.persistence.audit import audit_events

metadata = MetaData()
workflow_history = Table('advisory_workflow_history', metadata,
    Column('id',PGUUID(as_uuid=True),primary_key=True),
    Column('organization_id',PGUUID(as_uuid=True),nullable=False),
    Column('engagement_id',PGUUID(as_uuid=True),nullable=False),
    Column('event_type',String(40),nullable=False),
    Column('before_status',String(30)),
    Column('after_status',String(30),nullable=False),
    Column('actor_ref',String(120),nullable=False),
    Column('note',String(2000)),
    Column('occurred_at',DateTime(timezone=True),nullable=False))
approvals = Table('advisory_approvals', metadata,
    Column('id',PGUUID(as_uuid=True),primary_key=True),
    Column('organization_id',PGUUID(as_uuid=True),nullable=False),
    Column('engagement_id',PGUUID(as_uuid=True),nullable=False),
    Column('requested_by',String(120),nullable=False),
    Column('state',String(20),nullable=False),
    Column('reviewed_by',String(120)),
    Column('requested_at',DateTime(timezone=True),nullable=False),
    Column('reviewed_at',DateTime(timezone=True)),
    Column('note',String(2000)))
TRANSITIONS = {
    'proposed': {'cancelled'},
    'active': {'paused','completed','cancelled'},
    'paused': {'active','cancelled'},
    'completed': set(),
    'cancelled': set(),
}
class ApprovalRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    actor_ref: str=Field(min_length=1,max_length=120)
    note: str|None=Field(default=None,max_length=2000)
class ApprovalDecision(BaseModel):
    model_config=ConfigDict(extra='forbid')
    decision: Literal['approved','rejected']
    actor_ref: str=Field(min_length=1,max_length=120)
    note: str|None=Field(default=None,max_length=2000)
class AdvisoryTransition(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status: Literal['active','paused','completed','cancelled']
    actor_ref: str=Field(min_length=1,max_length=120)
    note: str|None=Field(default=None,max_length=2000)

def _engagement(db, tenant, eid, lock=False):
    q=select(TABLES['advisory_engagements'].c.payload).where(and_(TABLES['advisory_engagements'].c.id==eid,TABLES['advisory_engagements'].c.organization_id==tenant))
    if lock:q=q.with_for_update()
    obj=db.execute(q).scalar_one_or_none()
    if obj is None:raise HTTPException(404,'Advisory engagement not found')
    return obj

def _history(db, tenant, eid, kind, before, after, actor, note, now):
    db.execute(insert(workflow_history).values(id=uuid4(),organization_id=tenant,engagement_id=eid,event_type=kind,before_status=before,after_status=after,actor_ref=actor,note=note,occurred_at=now))

def _audit(db, tenant, eid, operation, now):
    db.execute(insert(audit_events).values(organization_id=tenant,record_type='advisory_engagements',record_id=eid,operation=operation,recorded_at=now))

def _change(db, tenant, eid, obj, status, now):
    out={**obj,'status':status,'updated_at':now.isoformat()}
    db.execute(update(TABLES['advisory_engagements']).where(and_(TABLES['advisory_engagements'].c.id==eid,TABLES['advisory_engagements'].c.organization_id==tenant)).values(payload=out,updated_at=now))
    return out

def create_engagement(payload, tenant, db):
    model=AdvisoryEngagement.model_validate(payload)
    obj=serialize(model,tenant)
    if model.classification.value=='public':raise HTTPException(422,'Advisory engagement may not be public')
    if model.status!='proposed':raise HTTPException(422,'Engagement must start proposed')
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
            db.execute(insert(TABLES['advisory_engagements']).values(**row))
            now=datetime.now(timezone.utc)
            _history(db,tenant,model.id,'created',None,'proposed','system:service',None,now)
            _audit(db,tenant,model.id,'created',now)
        return obj
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Duplicate engagement or legacy identity')

def request_approval(tenant, eid, request, db):
    with db.begin():
        obj=_engagement(db,tenant,eid,lock=True)
        if obj['status']!='proposed':raise HTTPException(409,'Only proposed engagements can request activation approval')
        if db.execute(select(approvals.c.id).where(and_(approvals.c.organization_id==tenant,approvals.c.engagement_id==eid,approvals.c.state=='pending'))).first():
            raise HTTPException(409,'Approval already pending')
        now=datetime.now(timezone.utc); aid=uuid4()
        db.execute(insert(approvals).values(id=aid,organization_id=tenant,engagement_id=eid,requested_by=request.actor_ref,state='pending',requested_at=now,note=request.note))
        _history(db,tenant,eid,'approval_requested','proposed','proposed',request.actor_ref,request.note,now)
    return {'approval_id':str(aid),'engagement_id':str(eid),'state':'pending'}

def decide_approval(tenant, eid, aid, decision, db):
    with db.begin():
        obj=_engagement(db,tenant,eid,lock=True)
        ap=db.execute(select(approvals).where(and_(approvals.c.id==aid,approvals.c.organization_id==tenant,approvals.c.engagement_id==eid)).with_for_update()).mappings().one_or_none()
        if ap is None:raise HTTPException(404,'Approval not found')
        if ap['state']!='pending':raise HTTPException(409,'Approval already decided')
        if obj['status']!='proposed':raise HTTPException(409,'Engagement no longer proposed')
        if ap['requested_by']==decision.actor_ref:raise HTTPException(403,'Requester may not approve own request')
        now=datetime.now(timezone.utc)
        db.execute(update(approvals).where(and_(approvals.c.id==aid,approvals.c.organization_id==tenant)).values(state=decision.decision,reviewed_by=decision.actor_ref,reviewed_at=now,note=decision.note))
        to='active' if decision.decision=='approved' else 'proposed'
        if to=='active':_change(db,tenant,eid,obj,'active',now);_audit(db,tenant,eid,'updated',now)
        _history(db,tenant,eid,'approval_'+decision.decision,'proposed',to,decision.actor_ref,decision.note,now)
    return {'approval_id':str(aid),'engagement_id':str(eid),'state':decision.decision,'status':to}

def transition(tenant,eid,change,db):
    with db.begin():
        obj=_engagement(db,tenant,eid,lock=True)
        before=obj['status']
        if change.status not in TRANSITIONS[before]:raise HTTPException(409,f'Invalid advisory transition: {before} -> {change.status}')
        now=datetime.now(timezone.utc)
        out=_change(db,tenant,eid,obj,change.status,now)
        _history(db,tenant,eid,'transition',before,change.status,change.actor_ref,change.note,now)
        _audit(db,tenant,eid,'updated',now)
    return out

def history(tenant,eid,db,limit=50):
    if not 1<=limit<=100:raise HTTPException(422,'Limit must be 1..100')
    _engagement(db,tenant,eid)
    rows=db.execute(select(workflow_history).where(and_(workflow_history.c.organization_id==tenant,workflow_history.c.engagement_id==eid)).order_by(workflow_history.c.occurred_at,workflow_history.c.id).limit(limit)).mappings()
    return {'items':[{k:str(v) if isinstance(v,UUID) else v.isoformat() if isinstance(v,datetime) else v for k,v in row.items()} for row in rows]}
