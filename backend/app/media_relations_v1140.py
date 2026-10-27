"""Synthetic media classification and embargo-aware press previews; never outreach."""
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, plain, opaque, SubscriptionPreference
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/media-relations',tags=['media-relations-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_MEDIA_STAGING_ENABLED')
BLOCKED_ACTIONS=('send','publish','enqueue','schedule','export-contacts','activate','delete','federate')


class OutletClassification(Fixture):
    outlet_ref: str = Field(pattern=r'^synthetic:[0-9a-f-]{36}$',max_length=46)
    kind: Literal['academic','trade','general','policy','broadcast']
    topics: list[Literal['climate','energy','methods','policy','society']] = Field(min_length=1,max_length=5)
    suppressed: StrictBool = False

    @field_validator('outlet_ref')
    @classmethod
    def synthetic_ref(cls,v):return SubscriptionPreference.canonical_subscriber(v)

    @field_validator('topics')
    @classmethod
    def unique_topics(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Repeated topics')
        return v


class PressPackage(Fixture):
    package_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(min_length=1,max_length=48,pattern=r'^[A-Za-z0-9_.:-]+$')
    headline: str = Field(min_length=1,max_length=180)
    pitch: str = Field(min_length=1,max_length=600)
    source_refs: list[str] = Field(min_length=1,max_length=12)
    spokesperson_ref: str = Field(pattern=r'^synthetic:[0-9a-f-]{36}$',max_length=46)
    as_of: datetime
    embargo_until: datetime | None = None
    review_state: Literal['draft','review','approved-preview','denied']='draft'
    rights_reviewed: StrictBool=False
    sources_verified: StrictBool=False
    spokesperson_verified: StrictBool=False
    institutional_approved: StrictBool=False
    editorial_reviewed: StrictBool=False
    privacy_reviewed: StrictBool=False
    suppressed: StrictBool=False
    outlets: list[OutletClassification] = Field(min_length=1,max_length=50)

    @field_validator('package_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('spokesperson_ref')
    @classmethod
    def speaker(cls,v):return SubscriptionPreference.canonical_subscriber(v)

    @field_validator('headline','pitch')
    @classmethod
    def text(cls,v):return plain(v)

    @field_validator('source_refs')
    @classmethod
    def sources(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Repeated sources')
        return [opaque(x) for x in v]

    @field_validator('as_of','embargo_until')
    @classmethod
    def aware(cls,v):
        if v is not None and (v.tzinfo is None or v.utcoffset() is None):raise ValueError('Timezone required')
        return v

    @model_validator(mode='after')
    def bounded_outlets(self):
        if len({x.outlet_ref for x in self.outlets})!=len(self.outlets):raise ValueError('Repeated outlet')
        if any(x.organization_id!=self.organization_id for x in self.outlets):raise ValueError('Cross-tenant fixture')
        return self


def assess(payload:PressPackage, tenant:str):
    if payload.organization_id!=tenant:raise ValueError('Tenant mismatch')
    gates={key:getattr(payload,key) for key in ('rights_reviewed','sources_verified','spokesperson_verified','institutional_approved','editorial_reviewed','privacy_reviewed')}
    embargo_active=payload.embargo_until is not None and payload.as_of < payload.embargo_until
    eligible=all(gates.values()) and payload.review_state=='approved-preview' and not payload.suppressed and not embargo_active
    normalized=payload.model_dump(mode='json')
    normalized['as_of']=payload.as_of.astimezone(timezone.utc).isoformat()
    normalized['embargo_until']=payload.embargo_until.astimezone(timezone.utc).isoformat() if payload.embargo_until else None
    normalized['source_refs']=sorted(payload.source_refs)
    normalized['outlets']=sorted(normalized['outlets'],key=lambda x:x['outlet_ref'])
    for outlet in normalized['outlets']:outlet['topics'].sort()
    return seal({'mode':'offline-synthetic-press-preview','fixture':normalized,'review_gates':gates,
                 'embargo_active':embargo_active,'review_complete_for_preview_only':all(gates.values()),
                 'pitch_preview':payload.pitch if eligible else None,
                 'eligible_synthetic_outlets':[x.outlet_ref for x in sorted(payload.outlets,key=lambda x:x.outlet_ref) if eligible and not x.suppressed]},tenant,'11.4.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-synthetic-media-relations','contact_collection_enabled':False},str(tenant),'11.4.0')


@router.post('/preview')
def preview(payload:PressPackage,tenant=Depends(_scope)):
    try:return assess(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/send')
@router.post('/publish')
@router.post('/enqueue')
@router.post('/schedule')
@router.post('/export-contacts')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live press operations disabled')
