"""Offline synthetic readership aggregates; no tracking or individual output."""
import hashlib
import json
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque, SubscriptionPreference
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/audience-analytics',tags=['audience-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_AUDIENCE_STAGING_ENABLED')
BLOCKED_ACTIONS=('track','collect','export-identities','publish','send','activate','delete','federate')


class MetricSource(Fixture):
    source_ref: str = Field(min_length=3,max_length=96)
    edition: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    measurement_basis: Literal['synthetic-fixture']='synthetic-fixture'

    @field_validator('source_ref')
    @classmethod
    def reference(cls,v):return opaque(v)


class AudienceEvent(Fixture):
    event_ref: str = Field(max_length=46)
    reader_ref: str = Field(max_length=46)
    object_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    channel: Literal['newsroom','feed','newsletter','event','embed']
    kind: Literal['view','engage']
    occurred_day: date
    source_ref: str = Field(min_length=3,max_length=96)

    @field_validator('event_ref','reader_ref')
    @classmethod
    def synthetic_reference(cls,v):return SubscriptionPreference.canonical_subscriber(v)

    @field_validator('object_ref','source_ref')
    @classmethod
    def reference(cls,v):return opaque(v)


class AudienceBatch(Fixture):
    events: list[AudienceEvent] = Field(min_length=1,max_length=500)
    sources: list[MetricSource] = Field(min_length=1,max_length=20)
    minimum_group_size: int = Field(default=5,strict=True,ge=5,le=50)

    @model_validator(mode='after')
    def integrity(self):
        if any(x.organization_id!=self.organization_id for x in [*self.events,*self.sources]):raise ValueError('Cross-tenant metrics')
        refs={s.source_ref for s in self.sources}
        if len(refs)!=len(self.sources):raise ValueError('Repeated source')
        if any(e.source_ref not in refs for e in self.events):raise ValueError('Missing source provenance')
        seen={}
        views=set()
        for e in self.events:
            data=e.model_dump(mode='json')
            if e.event_ref in seen and seen[e.event_ref]!=data:raise ValueError('Conflicting duplicate event')
            seen[e.event_ref]=data
            if e.kind=='view':views.add((e.reader_ref,e.channel,e.object_ref,e.revision))
        if any((e.reader_ref,e.channel,e.object_ref,e.revision) not in views for e in self.events if e.kind=='engage'):
            raise ValueError('Engagement requires matching synthetic view')
        return self


def aggregate_audience(batch:AudienceBatch,tenant:str):
    if batch.organization_id!=tenant:raise ValueError('Tenant mismatch')
    # Deduplicate replayed identical records before aggregation. Never echo IDs.
    events={e.event_ref:e for e in batch.events}
    channels=sorted({e.channel for e in events.values()})
    rows=[];suppressed=False
    for channel in channels:
        readers={e.reader_ref for e in events.values() if e.channel==channel and e.kind=='view'}
        engaged={e.reader_ref for e in events.values() if e.channel==channel and e.kind=='engage'}
        if len(readers)<batch.minimum_group_size or (engaged and len(engaged)<batch.minimum_group_size):
            suppressed=True;continue
        rows.append({'channel':channel,'distinct_synthetic_readers':len(readers),'distinct_synthetic_engaged_readers':len(engaged),'descriptive_engagement_share':round(len(engaged)/len(readers),4)})
    normalized={'events':sorted([e.model_dump(mode='json') for e in events.values()],key=lambda x:x['event_ref']),
                'sources':sorted([s.model_dump(mode='json') for s in batch.sources],key=lambda x:x['source_ref']),
                'minimum_group_size':batch.minimum_group_size}
    fingerprint=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    # Withhold the whole table if any nonzero cell is too small. No marginal
    # totals, suppressed labels or denominators that reveal a small residual.
    return seal({'mode':'offline-synthetic-audience-aggregate','method_version':'1190-distinct-readers-v1','rows':None if suppressed else rows,
                 'suppression_applied':suppressed,'minimum_group_size':batch.minimum_group_size,'input_sha256':fingerprint,
                 'provenance':[s.model_dump(mode='json') for s in sorted(batch.sources,key=lambda x:x.source_ref)],
                 'measurement_basis':'synthetic-fixture-only','deduplication':'identical-event-ref-replay-removed; readers-distinct-within-channel',
                 'causal_interpretation':'none; descriptive synthetic share only','tracking_enabled':False,'identity_export_enabled':False,
                 'historical_records_queried':0,'privacy_scope':'bounded synthetic fixture; not differential privacy or cross-query protection'},tenant,'11.9.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-synthetic-audience-aggregate','tracking_enabled':False,'identity_export_enabled':False},str(tenant),'11.9.0')


@router.post('/preview')
def preview(payload:AudienceBatch,tenant=Depends(_scope)):
    try:return aggregate_audience(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/track')
@router.post('/collect')
@router.post('/export-identities')
@router.post('/publish')
@router.post('/send')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live audience operations disabled')
