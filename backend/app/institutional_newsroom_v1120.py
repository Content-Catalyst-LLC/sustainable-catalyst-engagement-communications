"""Institutional newsroom synthetic announcement and release-history previews.

Zero persistence, publication, transport, external fetching, or production activation.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .research_distribution_v1100 import _scope
from .production_acceptance_v1090 import GATES as LIVE_GATES

router=APIRouter(prefix='/v1/institutional-newsroom',tags=['institutional-newsroom-staging'])
ANNOUNCEMENT_KINDS=('research-release','institutional-update','methodology-note','data-release','event-notice')
STATES=('draft','editorial-review','approved-preview','archived-preview')
BLOCKED_ACTIONS=('publish','release','syndicate','enqueue','send','activate','delete','federate')
REVIEW_GATES=('editorial','source-integrity','rights','privacy','institutional-approval','production-acceptance')

def canonical_url(value:str)->str:
    v=urlsplit(value)
    if (v.scheme!='https' or not v.hostname or v.username or v.password or v.fragment or
        v.port not in (None,443) or v.hostname in ('localhost','127.0.0.1','0.0.0.0') or
        v.hostname.endswith(('.local','.internal'))):
        raise ValueError('Canonical newsroom URL must be public HTTPS without fragment or credentials')
    return value

class NewsroomEntry(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    announcement_ref:str=Field(min_length=3,max_length=96,pattern=r'^[A-Za-z0-9_.:-]+$')
    revision:str=Field(min_length=1,max_length=48,pattern=r'^[A-Za-z0-9_.:-]+$')
    kind:Literal['research-release','institutional-update','methodology-note','data-release','event-notice']
    editorial_state:Literal['draft','editorial-review','approved-preview','archived-preview']='draft'
    headline:str=Field(min_length=1,max_length=180)
    summary:str=Field(min_length=1,max_length=600)
    canonical_url:str=Field(max_length=300)
    updated_at:datetime
    source_refs:list[str]=Field(min_length=1,max_length=12)
    rights_reviewed:bool=False
    editorial_reviewed:bool=False
    source_integrity_reviewed:bool=False
    privacy_reviewed:bool=False
    institutional_approved:bool=False

    @field_validator('canonical_url')
    @classmethod
    def validate_canonical(cls,v):return canonical_url(v)

    @field_validator('updated_at')
    @classmethod
    def aware(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('Timezone required')
        return v

    @field_validator('source_refs')
    @classmethod
    def sources(cls,v):
        if len(v)!=len(set(v)) or any(not re.fullmatch(r'[A-Za-z0-9_.:-]{3,96}',s) for s in v):
            raise ValueError('Source references must be unique opaque identifiers')
        return v

class NewsroomPreview(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    newsroom_title:str=Field(min_length=1,max_length=160)
    newsroom_url:str=Field(max_length=300)
    entries:list[NewsroomEntry]=Field(min_length=1,max_length=20)

    @field_validator('newsroom_url')
    @classmethod
    def validate_url(cls,v):return canonical_url(v)

    @model_validator(mode='after')
    def no_repeats(self):
        refs=[(e.announcement_ref,e.revision) for e in self.entries]
        if len(refs)!=len(set(refs)):raise ValueError('Repeated announcement revision')
        return self

def assess(payload:NewsroomPreview,organization_id:str)->dict:
    tenant=str(UUID(organization_id))
    if tenant!=organization_id:raise ValueError('Canonical organization UUID required')
    entries=sorted(payload.entries,key=lambda e:(e.announcement_ref,e.revision))
    output=[]
    for e in entries:
        gates={'editorial':e.editorial_reviewed,'source-integrity':e.source_integrity_reviewed,
               'rights':e.rights_reviewed,'privacy':e.privacy_reviewed,
               'institutional-approval':e.institutional_approved,'production-acceptance':False}
        output.append({'announcement_ref':e.announcement_ref,'revision':e.revision,'kind':e.kind,
                       'editorial_state':e.editorial_state,'headline':e.headline,'summary':e.summary,
                       'canonical_url':e.canonical_url,'updated_at':e.updated_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),
                       'source_refs':sorted(e.source_refs),'review_gates':gates,
                       'editorial_review_complete':all(v for k,v in gates.items() if k!='production-acceptance'),
                       'publication_authorized':False})
    document={'organization_id':tenant,'newsroom_title':payload.newsroom_title,
              'newsroom_url':payload.newsroom_url,'entries':output}
    canonical=json.dumps(document,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    return {'release':'11.2.0',**document,'sha256':hashlib.sha256(canonical.encode()).hexdigest(),
            'entry_count':len(output),'actual_publication_enabled':False,'outbound_communications_enabled':False,
            'persisted':False,'source_fetch_performed':False,'federation_enabled':False,
            'human_login_enabled':False,'deletion_enabled':False,'production_certified':False,
            'live_acceptance_gates_pending':list(LIVE_GATES)}

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'11.2.0','mode':'synthetic-newsroom-preview-only','organization_id':str(tenant),
            'production_certified':False,'actual_publication_enabled':False}

@router.post('/preview')
def preview(payload:NewsroomPreview,tenant=Depends(_scope)):
    try:return assess(payload,str(tenant))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/publish')
@router.post('/release')
@router.post('/syndicate')
@router.post('/enqueue')
@router.post('/send')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live newsroom actions disabled')
