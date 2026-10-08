from fastapi import Depends, FastAPI, Header, HTTPException
from .settings import Settings, validate_settings
from .domains.registry import DOMAINS
from .contracts.models import DomainDescriptor, HandoffEnvelope

settings = Settings()
validate_settings(settings)
app = FastAPI(title='Sustainable Catalyst Engagement & Communications', version='8.3.0', description='Opt-in tenant-scoped contact and engagement persistence; legacy WordPress untouched.')

def require_service_token(authorization: str | None = Header(default=None)) -> None:
    if settings.auth_mode == 'token':
        if authorization != 'Bearer ' + settings.service_token:
            raise HTTPException(status_code=401, detail='Unauthorized')

@app.get('/health')
def health():
    return {'status':'ok', 'service':'engagement-communications', 'version':'8.3.0', 'phase':'contact-engagement-migration'}

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
    return put_record(kind,payload,tenant,db)

@app.get('/v1/engagement/{kind}/{record_id}', dependencies=[Depends(require_service_token)])
def get_engagement(kind: str, record_id: UUID, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return read_record(kind,record_id,tenant,db)

@app.get('/v1/engagement/{kind}', dependencies=[Depends(require_service_token)])
def list_engagement(kind: str, limit: int = 50, offset: int = 0, tenant: UUID = Depends(get_tenant), db: Session = Depends(session)):
    return list_records(kind,tenant,db,limit,offset)
