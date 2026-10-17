"""Research distribution object foundation: source-traceable, nonpublishing synthetic previews."""
import hashlib
import json
import os
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .wordpress_bridge_certification_v1050 import DANGER_FLAGS
from .production_acceptance_v1090 import GATES as LIVE_GATES

router = APIRouter(prefix='/v1/research-distribution', tags=['research-distribution-staging'])
DISTRIBUTION_TARGETS=('rss','atom','json-feed','institutional-newsroom','newsletter','citation-index')
OBJECT_TYPES=('research-article','research-package','publication','dataset','methodology')
REQUIRED_REVIEW=('source_integrity','rights_and_license','editorial_approval','privacy_screening','distribution_approval','production_acceptance')
BLOCKED_ACTIONS=('publish','syndicate','enqueue','send','activate','federate','delete')

class DistributionPreview(BaseModel):
    model_config=ConfigDict(extra='forbid', str_strip_whitespace=True)
    object_ref: str = Field(min_length=3,max_length=96,pattern=r'^[A-Za-z0-9_.:-]+$')
    revision: str = Field(min_length=1,max_length=48,pattern=r'^[A-Za-z0-9_.:-]+$')
    object_kind: Literal['research-article','research-package','publication','dataset','methodology']
    targets: list[Literal['rss','atom','json-feed','institutional-newsroom','newsletter','citation-index']] = Field(min_length=1,max_length=6)
    source_refs: list[str] = Field(min_length=1,max_length=12)
    rights_basis: Literal['not-reviewed','author-owned','open-license','permission-required']='not-reviewed'
    editorial_reviewed: bool = False
    privacy_reviewed: bool = False
    source_integrity_reviewed: bool = False
    distribution_approved: bool = False

    @__import__('pydantic').field_validator('targets')
    @classmethod
    def unique_targets(cls,values):
        if len(values)!=len(set(values)):raise ValueError('Duplicate distribution targets')
        return values

    @__import__('pydantic').field_validator('source_refs')
    @classmethod
    def validate_sources(cls,values):
        import re
        if len(values)!=len(set(values)) or any(not re.fullmatch(r'[A-Za-z0-9_.:-]{3,96}',v) for v in values):
            raise ValueError('Source refs must be unique opaque identifiers')
        return values

def preview(payload:DistributionPreview,organization_id:str)->dict:
    tenant=str(UUID(organization_id))
    if tenant!=organization_id: raise ValueError('Noncanonical organization id')
    checks={
       'source_integrity':payload.source_integrity_reviewed,
       'rights_and_license':payload.rights_basis in ('author-owned','open-license'),
       'editorial_approval':payload.editorial_reviewed,
       'privacy_screening':payload.privacy_reviewed,
       'distribution_approval':payload.distribution_approved,
       'production_acceptance':False,
    }
    raw=json.dumps({'organization_id':tenant,'object_ref':payload.object_ref,
         'revision':payload.revision,'object_kind':payload.object_kind,
         'targets':sorted(payload.targets),'source_refs':sorted(payload.source_refs)},
         sort_keys=True,separators=(',',':')).encode()
    return {'release':'11.0.0','organization_id':tenant,'object_ref':payload.object_ref,
         'revision':payload.revision,'object_kind':payload.object_kind,
         'requested_targets':payload.targets,'source_count':len(payload.source_refs),
         'manifest_sha256':hashlib.sha256(raw).hexdigest(),
         'review_gates':checks,'human_review_complete':all(list(checks.values())[:-1]),
         'publication_authorized':False,'actual_publication_enabled':False,
         'actual_syndication_enabled':False,'outbound_communications_enabled':False,
         'persisted':False,'live_sources_fetched':False,'federation_enabled':False,
         'requires_live_production_acceptance':True,
         'live_acceptance_gates_pending':list(LIVE_GATES)}

def safety_state()->bool:
    return all(os.getenv(flag,'0')=='0' for flag in DANGER_FLAGS)

def _scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal)):
    if os.getenv('SCEC_DISTRIBUTION_STAGING_ENABLED','0')!='1' or not safety_state():
        raise HTTPException(503,'Research distribution staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound service identity required')
    tenant=tenant_for_principal(x_scec_organization_id,actor)
    allowlist={v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(tenant) not in allowlist:raise HTTPException(403,'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator','service'}):raise HTTPException(403,'Privileged role required')
    return tenant

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'11.0.0','organization_id':str(tenant),'mode':'synthetic-preview-only',
            'distribution_targets':DISTRIBUTION_TARGETS,'review_gates':REQUIRED_REVIEW,
            'publishing_enabled':False,'outbound_enabled':False,'production_certified':False}

@router.post('/manifest-preview')
def manifest_preview(payload:DistributionPreview,tenant=Depends(_scope)):
    try:return preview(payload,str(tenant))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/publish')
@router.post('/syndicate')
@router.post('/enqueue')
@router.post('/send')
@router.post('/activate')
@router.post('/federate')
@router.post('/delete')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Distribution and production actions disabled')
