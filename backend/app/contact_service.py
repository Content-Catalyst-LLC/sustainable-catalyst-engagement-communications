"""v8.3 tenant-scoped service. No WordPress calls or automated legacy imports."""
import os
from datetime import datetime, timezone
from uuid import UUID
from fastapi import Depends, Header, HTTPException
from sqlalchemy import create_engine, select, and_, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.contracts.canonical import MODEL_REGISTRY, Organization, Contact, Inquiry, EngagementEvent
from app.persistence.models import TABLES, metadata

ALLOWED = {'organizations', 'contacts', 'inquiries', 'engagement_events'}

def config():
    if os.getenv('SCEC_PERSISTENCE_ENABLED') != '1':
        raise HTTPException(503, 'Persistence endpoints disabled')
    url = os.getenv('SCEC_DATABASE_URL', '')
    if not url.startswith('postgresql+psycopg://'):
        raise HTTPException(503, 'Dedicated PostgreSQL URL required')
    if '/scec_engagement_' not in url.split('?',1)[0]:
        raise HTTPException(503, 'Refusing database outside dedicated Engagement namespace')
    allowed={s.strip() for s in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if s.strip()}
    if not allowed:
        raise HTTPException(503, 'Organization allowlist not configured')
    return url, allowed

def get_tenant(x_scec_organization_id: str | None = Header(default=None)) -> UUID:
    url, allowed=config()
    try: tenant=UUID(x_scec_organization_id or '')
    except ValueError: raise HTTPException(400,'Valid X-SCEC-Organization-ID required')
    if str(tenant) not in allowed:
        raise HTTPException(403,'Organization not authorized for this service')
    return tenant

def session():
    url,_=config()
    engine=create_engine(url,pool_pre_ping=True,pool_size=2,max_overflow=0)
    try:
        with Session(engine) as db: yield db
    finally:engine.dispose()

def serialize(model, tenant):
    if model.organization_id != tenant and not (isinstance(model,Organization) and model.id == tenant and model.organization_id in (None,tenant)):
        raise HTTPException(403,'Organization mismatch')
    obj=model.model_dump(mode='json')
    if isinstance(model,Organization): obj['organization_id']=str(tenant)
    return obj

def put_record(kind: str, payload: dict, tenant: UUID, db: Session):
    if kind not in ALLOWED: raise HTTPException(404,'Unknown record type')
    model=MODEL_REGISTRY[kind].model_validate(payload)
    obj=serialize(model,tenant)
    table=TABLES[kind]
    legacy=model.legacy_identity
    row=dict(id=model.id,organization_id=tenant,schema_version=model.schema_version,
             classification=model.classification.value,created_at=model.created_at,updated_at=model.updated_at,
             legacy_system=legacy.system.value if legacy else None,
             legacy_object_type=legacy.object_type if legacy else None,
             legacy_external_id=legacy.external_id if legacy else None,payload=obj)
    try:
        with db.begin():
            if kind!='organizations':
                org=db.execute(select(TABLES['organizations'].c.id).where(TABLES['organizations'].c.id==tenant)).first()
                if org is None: raise HTTPException(422,'Organization must be registered first')
        if kind=='inquiries' and model.contact_id is not None:
            contact=db.execute(select(TABLES['contacts'].c.id).where(and_(TABLES['contacts'].c.id==model.contact_id,TABLES['contacts'].c.organization_id==tenant))).first()
            if not contact:raise HTTPException(422,'contact_id must belong to the same organization')
            db.execute(insert(table).values(**row))
            if kind!='engagement_events':
                from app.persistence.audit import audit_events
                db.execute(insert(audit_events).values(organization_id=tenant,record_type=kind,record_id=model.id,operation='created',recorded_at=datetime.now(timezone.utc)))
        return obj
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Duplicate record or legacy identity')

def read_record(kind: str, record_id: UUID, tenant: UUID, db: Session):
    if kind not in ALLOWED: raise HTTPException(404,'Unknown record type')
    table=TABLES[kind]
    result=db.execute(select(table.c.payload).where(and_(table.c.id==record_id,table.c.organization_id==tenant))).scalar_one_or_none()
    if result is None: raise HTTPException(404,'Record not found')
    return result

def list_records(kind: str, tenant: UUID, db: Session, limit: int=50, offset: int=0):
    if kind not in ALLOWED: raise HTTPException(404,'Unknown record type')
    if not (1<=limit<=100 and 0<=offset<=100000):raise HTTPException(422,'Invalid pagination')
    table=TABLES[kind]
    result=db.execute(select(table.c.payload).where(table.c.organization_id==tenant).order_by(table.c.created_at.desc(),table.c.id).limit(limit).offset(offset)).scalars().all()
    return {'items':result,'limit':limit,'offset':offset}
