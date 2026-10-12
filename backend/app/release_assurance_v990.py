"""v9.9.0 staging-only security and release readiness assessments; no side effects."""
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, principal, bound_mode, tenant_for_principal

router=APIRouter(prefix='/v1/release-assurance',tags=['release-assurance-staging'])
VERSION='9.9.0'
GATES=('public_https_dns_tls','wordpress_public_launcher_acceptance','authenticated_human_session',
       'csrf_revocation_session_expiry','live_tenant_isolation_roles','privacy_retention_policy',
       'staged_persistence_write_certification')
FORBIDDEN=('SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED')

class Evidence(BaseModel):
    model_config=ConfigDict(extra='forbid')
    gate:str=Field(min_length=3,max_length=100)
    verified:bool=False
    evidence_reference:str|None=Field(default=None,max_length=160,pattern=r'^[a-zA-Z0-9_./:-]+$')

class Assessment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    evidence:list[Evidence]=Field(default_factory=list,max_length=7)


def guard(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv('SCEC_ASSURANCE_STAGING_ENABLED','0')!='1':
        raise HTTPException(503,'Release assurance staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound identity required')
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(org) not in allowed:raise HTTPException(403,'Organization not allowlisted')
    if not actor.roles.intersection({'administrator'}):raise HTTPException(403,'Administrator required')
    return org


def evaluate(evidence:list[Evidence]):
    if len({e.gate for e in evidence})!=len(evidence):raise HTTPException(422,'Duplicate gates')
    if any(e.gate not in GATES for e in evidence):raise HTTPException(422,'Unknown certification gate')
    # Supplied assertions are NOT independent certification or authorization.
    supplied={e.gate:e for e in evidence}
    flags={name:os.getenv(name,'0') for name in FORBIDDEN}
    unsafe_flags=[name for name,value in flags.items() if value!='0']
    review=[{'gate':gate,'submitted_verified':bool(supplied.get(gate) and supplied[gate].verified),
             'reference_present':bool(supplied.get(gate) and supplied[gate].evidence_reference),
             'independently_verified':False} for gate in GATES]
    return {'release':VERSION,'assessment_only':True,'source_preflight_not_replaced':True,
            'production_certified':False,'production_writes_enabled':False,
            'outbound_communications_enabled':False,'actual_deletion_enabled':False,
            'actual_federation_enabled':False,'enabled_forbidden_flags':unsafe_flags,
            'evidence':review,'gates_not_independently_certified':list(GATES),
            'requires_human_approval':True,'promotion_permitted':False}

def digest(report:dict)->str:
    return hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@router.get('/status')
def status(org:UUID=Depends(guard)):
    return {'release':VERSION,'organization_id':str(org),'staging':True,'production_certified':False,
            'mutation_permitted':False,'outbound_permitted':False,'deletion_permitted':False,'federation_permitted':False}

@router.post('/assessment-preview')
def assessment(payload:Assessment,org:UUID=Depends(guard)):
    result=evaluate(payload.evidence)
    return {'organization_id':str(org),'report':result,'report_sha256':digest(result),'persisted':False,'transmitted':False}

@router.get('/reliability-preview')
def reliability(org:UUID=Depends(guard)):
    # No outbound network calls, DB probing, retries, or assertions of uptime.
    report={'release':VERSION,'readiness':'staging-only','backend':'requires-separate-local-health-check',
            'frontend':'requires-separate-local-readonly-check','db':'not-probed',
            'outbound':'not-probed','wordpress':'not-probed','production_certified':False}
    return {'organization_id':str(org),'report':report,'report_sha256':digest(report)}

@router.post('/promote')
@router.post('/commit')
@router.post('/enable-writes')
@router.post('/enable-outbound')
@router.post('/enable-deletion')
@router.post('/enable-federation')
def denied(org:UUID=Depends(guard)):
    raise HTTPException(503,'Promotion and real operations are disabled in v9.9.0')
