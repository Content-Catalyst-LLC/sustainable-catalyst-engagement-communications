from fastapi import Depends, FastAPI, Header, HTTPException
from .settings import Settings, validate_settings
from .domains.registry import DOMAINS
from .contracts.models import DomainDescriptor, HandoffEnvelope

settings = Settings()
validate_settings(settings)
app = FastAPI(title='Sustainable Catalyst Engagement & Communications', version='8.5.0', description='Opt-in tenant-scoped contact and engagement persistence; legacy WordPress untouched.')

def require_service_token(authorization: str | None = Header(default=None)) -> None:
    if settings.auth_mode == 'token':
        if authorization != 'Bearer ' + settings.service_token:
            raise HTTPException(status_code=401, detail='Unauthorized')

@app.get('/health')
def health():
    return {'status':'ok', 'service':'engagement-communications', 'version':'8.5.0', 'phase':'advisory-institutional-workflows'}

@app.get('/v1/capabilities', response_model=list[DomainDescriptor], dependencies=[Depends(require_service_token)])
def capabilities():
    return list(DOMAINS)

@app.post('/v1/contracts/handoff/validate', dependencies=[Depends(require_service_token)])
def validate_handoff(payload: HandoffEnvelope):
    return {'valid':True,'contract_version':payload.contract_version,'correlation_id':payload.correlation_id,'action':'none','requires_human_approval':True}

# Read-only contract discovery. Never accepts or writes production records.
from .contracts.canonical import MODEL_REGISTRY, CONTRACT_VERSION

@app.get('/v1/contracts/canonical', dependencies=[Depends(require_service_token)])
def canonical_contracts():
    return {"version": CONTRACT_VERSION, "persistence": "opt-in-postgresql", "models": sorted(MODEL_REGISTRY)}

@app.get('/v1/contracts/canonical/{model_name}/schema', dependencies=[Depends(require_service_token)])
def canonical_schema(model_name: str):
    model = MODEL_REGISTRY.get(model_name)
    if model is None:
        raise HTTPException(status_code=404, detail="Unknown canonical model")
    return model.model_json_schema()

# Service-to-service endpoints. Tokens authorize only an explicitly allowlisted organization.
from uuid import UUID
from fastapi import Body
from sqlalchemy.orm import Session
from .contact_service import get_tenant, session, put_record, read_record, list_records

@app.post('/v1/engagement/{kind}', status_code=201, dependencies=[Depends(require_service_token)])
def create_engagement(kind: str, payload: dict = Body(...), tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    if kind == 'cases': raise HTTPException(404, 'Use support case workflow')
    return put_record(kind,payload,tenant,db)

@app.get('/v1/engagement/{kind}/{record_id}', dependencies=[Depends(require_service_token)])
def get_engagement(kind: str, record_id: UUID, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return read_record(kind,record_id,tenant,db)

@app.get('/v1/engagement/{kind}', dependencies=[Depends(require_service_token)])
def list_engagement(kind: str, limit: int = 50, offset: int = 0, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return list_records(kind,tenant,db,limit,offset)

# v8.4.0 support workflows: authenticated, organization-scoped, persistence opt-in.
from .support_service import CaseTransition, SupportFeedback, create_case, transition_case, add_feedback, case_history

@app.post('/v1/support/cases',status_code=201,dependencies=[Depends(require_service_token)])
def support_case_create(payload: dict = Body(...), tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return create_case(payload,tenant,db)

@app.get('/v1/support/cases/{case_id}',dependencies=[Depends(require_service_token)])
def support_case_read(case_id: UUID, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return read_record('cases',case_id,tenant,db)

@app.get('/v1/support/cases',dependencies=[Depends(require_service_token)])
def support_case_list(limit: int=50, offset: int=0, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return list_records('cases',tenant,db,limit,offset)

@app.post('/v1/support/cases/{case_id}/transitions',dependencies=[Depends(require_service_token)])
def support_case_transition(case_id: UUID, change: CaseTransition, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return transition_case(tenant,case_id,change,db)

@app.post('/v1/support/cases/{case_id}/feedback',status_code=201,dependencies=[Depends(require_service_token)])
def support_case_feedback(case_id: UUID, payload: SupportFeedback, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return add_feedback(tenant,case_id,payload,db)

@app.get('/v1/support/cases/{case_id}/history',dependencies=[Depends(require_service_token)])
def support_case_history(case_id: UUID, limit: int=50, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return case_history(tenant,case_id,db,limit)

# v8.5.0 institutional advisory workflow; service-authenticated and tenant scoped.
from .advisory_service import ApprovalRequest, ApprovalDecision, AdvisoryTransition
from .advisory_service import create_engagement as advisory_create, request_approval, decide_approval, transition as advisory_transition, history as advisory_history

@app.post('/v1/advisory/engagements',status_code=201,dependencies=[Depends(require_service_token)])
def advisory_engagement_create(payload: dict = Body(...), tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return advisory_create(payload,tenant,db)

@app.get('/v1/advisory/engagements/{engagement_id}',dependencies=[Depends(require_service_token)])
def advisory_engagement_read(engagement_id: UUID, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    from .advisory_service import _engagement
    return _engagement(db,tenant,engagement_id)

@app.get('/v1/advisory/engagements',dependencies=[Depends(require_service_token)])
def advisory_engagement_list(limit: int = 50, offset: int = 0, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    from sqlalchemy import select
    from .persistence.models import TABLES
    if not 1 <= limit <= 100 or not 0 <= offset <= 100000:raise HTTPException(422,'Invalid pagination')
    table=TABLES['advisory_engagements']
    items=db.execute(select(table.c.payload).where(table.c.organization_id==tenant).order_by(table.c.created_at.desc(),table.c.id).limit(limit).offset(offset)).scalars().all()
    return {'items':items,'limit':limit,'offset':offset}

@app.post('/v1/advisory/engagements/{engagement_id}/approvals',status_code=201,dependencies=[Depends(require_service_token)])
def advisory_approval_request(engagement_id: UUID, payload: ApprovalRequest, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return request_approval(tenant,engagement_id,payload,db)

@app.post('/v1/advisory/engagements/{engagement_id}/approvals/{approval_id}/decision',dependencies=[Depends(require_service_token)])
def advisory_approval_decide(engagement_id: UUID, approval_id: UUID, payload: ApprovalDecision, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return decide_approval(tenant,engagement_id,approval_id,payload,db)

@app.post('/v1/advisory/engagements/{engagement_id}/transitions',dependencies=[Depends(require_service_token)])
def advisory_status_transition(engagement_id: UUID, payload: AdvisoryTransition, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return advisory_transition(tenant,engagement_id,payload,db)

@app.get('/v1/advisory/engagements/{engagement_id}/history',dependencies=[Depends(require_service_token)])
def advisory_engagement_history(engagement_id: UUID, limit: int=50, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return advisory_history(tenant,engagement_id,db,limit)
