"""v9.7 governance: deterministic policy planning on request-supplied metadata only.
No data removal, consent mutation, external messaging, persistent store, or background jobs.
Not a substitute for an approved legal retention policy.
"""
import hashlib
import json
import os
from collections import Counter
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router=APIRouter(prefix='/v1/privacy-governance',tags=['privacy-governance-staging'])
PURPOSES={'contact-response','support-resolution','feature-feedback','community-participation','institutional-advisory','communications','analytics'}
CATEGORIES={'contact','feedback','feature-suggestions','channel','support','institutional','communications'}
BASES={'consent','contract','legitimate-interest','legal-obligation','public-task','unspecified'}
CONSENT={'granted','denied','withdrawn','not-recorded','not-applicable'}
ACTIONS={'access-request','rectification-request','erasure-request','restriction-request','consent-withdrawal','retention-review'}
SENSITIVITY={'ordinary','elevated','sensitive'}

class GovernanceItem(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    channel:str
    purpose:str
    legal_basis:str='unspecified'
    consent_state:str='not-recorded'
    sensitivity:str='ordinary'
    collected_day:date|None=None
    retention_days:int|None=Field(default=None,ge=1,le=36500)
    deletion_hold:bool=False
    human_review_required:bool=True
    @model_validator(mode='after')
    def check(self):
        for f,values in (('channel',CATEGORIES),('purpose',PURPOSES),('legal_basis',BASES),('consent_state',CONSENT),('sensitivity',SENSITIVITY)):
            if getattr(self,f) not in values:raise ValueError('Unsupported '+f)
        return self

class Batch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    records:list[GovernanceItem]=Field(min_length=1,max_length=50)
    evaluation_day:date

class RightsRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_type:str
    identity_verified:bool=False
    legal_hold:bool=False
    cross_system_review_complete:bool=False
    @model_validator(mode='after')
    def check(self):
        if self.request_type not in ACTIONS:raise ValueError('Unsupported rights request')
        return self

def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv('SCEC_PRIVACY_STAGING_ENABLED','0')!='1':raise HTTPException(503,'Privacy governance staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound identity required')
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={x.strip() for x in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if x.strip()}
    if str(org) not in allowed:raise HTTPException(403,'Organization not allowlisted')
    if not actor.roles.intersection({'administrator','advisor'}):raise HTTPException(403,'Governance role required')
    return org

def inspect(item:GovernanceItem,asof:date)->dict:
    issues=[]
    if item.legal_basis=='unspecified':issues.append('legal-basis-review')
    if item.legal_basis=='consent' and item.consent_state!='granted':issues.append('consent-not-established')
    if item.sensitivity!='ordinary':issues.append('sensitivity-review')
    if item.collected_day and item.collected_day>asof:issues.append('future-collection-date')
    if item.retention_days is None or item.collected_day is None:issues.append('retention-insufficient-metadata')
    expires=(item.collected_day.toordinal()+item.retention_days) if item.collected_day and item.retention_days else None
    if expires is not None and expires<=asof.toordinal():issues.append('retention-review-due')
    if item.deletion_hold:issues.append('hold-review')
    return {'channel':item.channel,'purpose':item.purpose,'issues':sorted(issues),
            'policy_recommendation_only':True,'consent_verified':False,
            'erasure_authorized':False,'deadline_binding':False,
            'human_review_required':True}

def compute(batch:Batch)->dict:
    records=[inspect(x,batch.evaluation_day) for x in batch.records]
    return {'version':'9.7.0','preview_only':True,'count':len(records),'evaluation_day':batch.evaluation_day.isoformat(),
            'channel_counts':dict(sorted(Counter(x['channel'] for x in records).items())),
            'review_flag_counts':dict(sorted(Counter(flag for x in records for flag in x['issues']).items())),
            'privacy_impact_review_recommended':any(x['issues'] for x in records),
            'raw_records_included':False,'persisted':False,'consent_changed':False,'deleted':False,
            'outbound_enabled':False,'human_review_required':True,
            'disclaimer':'Advisory metadata preview only; no statutory deadline or legal determination.'}

def digest(report:dict)->str:
    return hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@router.get('/status')
def status(org:UUID=Depends(scope)):
    return {'version':'9.7.0','organization_id':str(org),'preview_only':True,'max_batch':50,
            'writes_enabled':False,'outbound_enabled':False,'deletion_enabled':False,'wordpress_bridge':'unchanged'}

@router.post('/policy-preview')
def policy_preview(payload:Batch,org:UUID=Depends(scope)):
    report=compute(payload)
    return {'version':'9.7.0','organization_id':str(org),'report':report,'deterministic_sha256':digest(report)}

@router.post('/rights-request-preview')
def rights_preview(payload:RightsRequest,org:UUID=Depends(scope)):
    flags=[]
    if not payload.identity_verified:flags.append('verify-requester-identity')
    if payload.legal_hold:flags.append('legal-hold-review')
    if not payload.cross_system_review_complete:flags.append('cross-system-review')
    return {'version':'9.7.0','organization_id':str(org),'request_type':payload.request_type,
            'review_flags':flags,'fulfillment_authorized':False,'deleted':False,
            'consent_changed':False,'persisted':False,'human_review_required':True}

@router.post('/delete')
def deletion_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Actual deletion disabled in v9.7.0')

@router.post('/consent-commit')
def consent_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Consent mutation disabled in v9.7.0')

@router.post('/commit')
def write_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Production writes disabled in v9.7.0')
