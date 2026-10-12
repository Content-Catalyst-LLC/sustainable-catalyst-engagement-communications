"""v9.8 federation CONTRACT previews only: no OIDC trust, token exchange, redirects, network or writes."""
import hashlib
import json
import os
from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router=APIRouter(prefix='/v1/federation-intelligence',tags=['federation-staging'])
PRODUCTS={'library','librarian','workspace','workbench','research-lab','site-intelligence','decision-studio','engagement-communications'}
CAPABILITIES={'view-public-summary','view-tenant-summary','start-support-preview','start-advisory-preview','view-engagement-summary'}
SENSITIVITY={'public','internal','restricted'}

class ApplicationHandoff(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    source_app:str
    destination_app:str
    requested_capability:str
    subject_reference:str=Field(min_length=6,max_length=120,pattern=r'^[a-zA-Z0-9._:-]+$')
    tenant_reference:UUID
    data_classification:str='internal'
    source_issuer_validated:bool=False
    destination_trust_registered:bool=False
    subject_mapping_reviewed:bool=False
    explicit_user_consent:bool=False
    @model_validator(mode='after')
    def validate_values(self):
        if self.source_app not in PRODUCTS or self.destination_app not in PRODUCTS:raise ValueError('Unsupported application')
        if self.requested_capability not in CAPABILITIES:raise ValueError('Unsupported capability')
        if self.data_classification not in SENSITIVITY:raise ValueError('Unsupported data classification')
        return self

class HandoffBatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    requests:list[ApplicationHandoff]=Field(min_length=1,max_length=25)

def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv('SCEC_FEDERATION_STAGING_ENABLED','0')!='1':raise HTTPException(503,'Federation previews disabled')
    if not bound_mode():raise HTTPException(503,'Bound identity required')
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={x.strip() for x in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if x.strip()}
    if str(org) not in allowed:raise HTTPException(403,'Organization not allowlisted')
    if not actor.roles.intersection({'administrator','advisor'}):raise HTTPException(403,'Federation review role required')
    return org

def evaluate(req:ApplicationHandoff,tenant:UUID)->dict:
    if req.tenant_reference!=tenant:raise HTTPException(403,'Cross-tenant reference rejected')
    flags=[]
    if req.source_app==req.destination_app:flags.append('same-application-route')
    if not req.source_issuer_validated:flags.append('source-issuer-not-validated')
    if not req.destination_trust_registered:flags.append('destination-trust-not-registered')
    if not req.subject_mapping_reviewed:flags.append('subject-mapping-review-required')
    if req.data_classification!='public' and not req.explicit_user_consent:flags.append('consent-review-required')
    if req.data_classification=='restricted':flags.append('restricted-data-review')
    return {'source_app':req.source_app,'destination_app':req.destination_app,
            'requested_capability':req.requested_capability,'data_classification':req.data_classification,
            'review_flags':flags,'preview_only':True,'federation_authorized':False,
            'token_exchanged':False,'identity_linked':False,'redirect_issued':False,
            'data_transferred':False,'persisted':False,'human_review_required':True}

def fingerprint(result:dict)->str:
    return hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@router.get('/status')
def status(org:UUID=Depends(scope)):
    return {'version':'9.8.0','organization_id':str(org),'preview_only':True,
            'federation_enabled':False,'token_exchange_enabled':False,'writes_enabled':False,
            'outbound_enabled':False,'deletion_enabled':False,'wordpress_bridge':'unchanged'}

@router.post('/handoff-preview')
def handoff_preview(payload:ApplicationHandoff,org:UUID=Depends(scope)):
    report=evaluate(payload,org)
    return {'version':'9.8.0','organization_id':str(org),'report':report,'deterministic_sha256':fingerprint(report)}

@router.post('/compatibility-preview')
def compatibility_preview(payload:HandoffBatch,org:UUID=Depends(scope)):
    results=[evaluate(item,org) for item in payload.requests]
    report={'count':len(results),'source_counts':dict(sorted(Counter(x['source_app'] for x in results).items())),
            'destination_counts':dict(sorted(Counter(x['destination_app'] for x in results).items())),
            'review_flag_counts':dict(sorted(Counter(flag for x in results for flag in x['review_flags']).items())),
            'federation_authorized':False,'data_transferred':False,'persisted':False,'human_review_required':True}
    return {'version':'9.8.0','organization_id':str(org),'report':report,'deterministic_sha256':fingerprint(report)}

@router.post('/token-exchange')
def token_exchange(org:UUID=Depends(scope)):
    raise HTTPException(503,'Federated token exchange disabled')
@router.post('/link-identity')
def link_identity(org:UUID=Depends(scope)):
    raise HTTPException(503,'Federated identity linking disabled')
@router.post('/handoff-commit')
def handoff_commit(org:UUID=Depends(scope)):
    raise HTTPException(503,'Federated handoffs disabled')
@router.post('/commit')
def commit(org:UUID=Depends(scope)):
    raise HTTPException(503,'Federation persistence disabled')
