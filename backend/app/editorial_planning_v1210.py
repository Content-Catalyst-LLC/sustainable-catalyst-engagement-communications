"""Deterministic editorial launch-window checks; no clock, cron or calendar writes."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, field_validator, model_validator
from .communication_objects_v1200 import FrozenFixture, CommunicationObject, EvidencePointer, preview_object
from .newsletter_alerts_v1130 import SyntheticPreviewRoute, opaque
from .events_v1160 import Event
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/editorial-planning',tags=['editorial-planning-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_CALENDAR_STAGING_ENABLED')
BLOCKED_ACTIONS=('schedule','start-cron','write-calendar','notify','publish','send','activate','delete','federate')


def utc(value):return value.astimezone(timezone.utc)


class ZonedWindow(FrozenFixture):
    starts_at: datetime
    ends_at: datetime
    timezone_name: str = Field(min_length=1,max_length=64)

    @field_validator('starts_at','ends_at')
    @classmethod
    def aware(cls,v):return Event.aware(v)

    @field_validator('timezone_name')
    @classmethod
    def zone(cls,v):return Event.zone(v)

    @model_validator(mode='after')
    def local_schedule(self):
        if utc(self.ends_at)<=utc(self.starts_at):raise ValueError('Positive window required')
        zone=ZoneInfo(self.timezone_name)
        for moment in (self.starts_at,self.ends_at):
            local=moment.astimezone(zone)
            if local.replace(tzinfo=None)!=moment.replace(tzinfo=None) or local.utcoffset()!=moment.utcoffset():raise ValueError('Timezone/offset mismatch')
        return self


class LaunchWindow(ZonedWindow):
    window_ref: str = Field(min_length=3,max_length=96)
    evidence: EvidencePointer
    depends_on: tuple[str,...] = Field(default_factory=tuple,max_length=20)
    embargo_until: datetime | None = None
    embargo_reviewed: StrictBool=False
    editorial_reviewed: StrictBool=False

    @field_validator('window_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('embargo_until')
    @classmethod
    def embargo(cls,v):return Event.aware(v) if v is not None else None

    @field_validator('depends_on')
    @classmethod
    def dependencies(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Repeated dependency')
        return tuple(sorted(opaque(x) for x in v))

    @model_validator(mode='after')
    def bounded(self):
        if self.evidence.organization_id!=self.organization_id:raise ValueError('Cross-tenant evidence')
        return self


class Blackout(ZonedWindow):
    blackout_ref: str = Field(min_length=3,max_length=96)

    @field_validator('blackout_ref')
    @classmethod
    def reference(cls,v):return opaque(v)


class EditorialPlan(FrozenFixture):
    plan_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    communication: CommunicationObject
    communication_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    as_of: datetime
    windows: tuple[LaunchWindow,...] = Field(min_length=1,max_length=30)
    blackouts: tuple[Blackout,...] = Field(default_factory=tuple,max_length=30)

    @field_validator('plan_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('as_of')
    @classmethod
    def aware(cls,v):return Event.aware(v)

    @model_validator(mode='after')
    def graph(self):
        if self.communication.organization_id!=self.organization_id or any(x.organization_id!=self.organization_id for x in [*self.windows,*self.blackouts]):raise ValueError('Cross-tenant plan')
        if self.communication_sha256!=preview_object(self.communication,self.organization_id)['sha256']:raise ValueError('Stale communication evidence')
        nodes={n.node_ref:n for n in self.communication.nodes}
        refs={w.window_ref:w for w in self.windows}
        if len(refs)!=len(self.windows) or len({b.blackout_ref for b in self.blackouts})!=len(self.blackouts):raise ValueError('Repeated window')
        for w in self.windows:
            if w.evidence.node_ref not in nodes or w.evidence.evidence_sha256!=nodes[w.evidence.node_ref].evidence_sha256:raise ValueError('Missing or stale artifact evidence')
            if any(ref not in refs for ref in w.depends_on):raise ValueError('Missing launch dependency')
        done=set()
        while len(done)<len(refs):
            available={ref for ref,w in refs.items() if ref not in done and set(w.depends_on).issubset(done)}
            if not available:raise ValueError('Cyclic launch dependency')
            done.update(available)
        return self


def simulate_plan(plan:EditorialPlan,tenant:str):
    if plan.organization_id!=tenant:raise ValueError('Tenant mismatch')
    windows={w.window_ref:w for w in plan.windows};decisions={}
    while len(decisions)<len(windows):
        for ref,w in sorted(windows.items()):
            if ref in decisions or any(dep not in decisions for dep in w.depends_on):continue
            reasons=[]
            if not w.embargo_reviewed:reasons.append('embargo-review-required')
            if not w.editorial_reviewed:reasons.append('editorial-review-required')
            if utc(w.starts_at)<utc(plan.as_of):reasons.append('window-in-past')
            if w.embargo_until and utc(w.starts_at)<utc(w.embargo_until):reasons.append('embargo-active')
            if any(utc(w.starts_at)<utc(b.ends_at) and utc(w.ends_at)>utc(b.starts_at) for b in plan.blackouts):reasons.append('blackout-overlap')
            for dep in w.depends_on:
                if not decisions[dep]['eligible_for_plan_only']:reasons.append('dependency-ineligible')
                if utc(w.starts_at)<utc(windows[dep].ends_at):reasons.append('dependency-not-finished')
            decisions[ref]={'window_ref':ref,'node_ref':w.evidence.node_ref,'proposed_start_utc':utc(w.starts_at).isoformat(),'proposed_end_utc':utc(w.ends_at).isoformat(),'eligible_for_plan_only':not reasons,'review_flags':sorted(set(reasons))}
    normalized=plan.model_dump(mode='json');normalized['windows'].sort(key=lambda x:x['window_ref']);normalized['blackouts'].sort(key=lambda x:x['blackout_ref']);normalized['communication']['nodes'].sort(key=lambda x:x['node_ref'])
    for w in normalized['windows']:
        for field in ('starts_at','ends_at','embargo_until'):
            if w[field]:w[field]=utc(getattr(windows[w['window_ref']],field)).isoformat()
    normalized['as_of']=utc(plan.as_of).isoformat()
    return seal({'mode':'offline-editorial-calendar-simulation','fixture':normalized,'windows':[decisions[k] for k in sorted(decisions)],'cron_enabled':False,'calendar_writes_enabled':False,'notifications_enabled':False,'automatic_rescheduling_enabled':False},tenant,'12.1.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-editorial-calendar-simulation','cron_enabled':False,'calendar_writes_enabled':False},str(tenant),'12.1.0')


@router.post('/preview')
def preview(payload:EditorialPlan,tenant=Depends(_scope)):
    try:return simulate_plan(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/schedule')
@router.post('/start-cron')
@router.post('/write-calendar')
@router.post('/notify')
@router.post('/publish')
@router.post('/send')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live calendar operations disabled')
