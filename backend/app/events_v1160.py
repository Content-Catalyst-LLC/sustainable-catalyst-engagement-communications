"""Synthetic event lifecycle and non-delivering RFC 5545 calendar previews."""
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque, SubscriptionPreference
from .citation_discovery_v1150 import text, public_url
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/events',tags=['events-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_EVENTS_STAGING_ENABLED')
BLOCKED_ACTIONS=('register','invite','broadcast','write-calendar','publish','send','schedule','delete','federate')


class Speaker(Fixture):
    speaker_ref: str = Field(max_length=46)
    attribution: str = Field(min_length=1,max_length=120)
    privacy_reviewed: StrictBool=False
    attribution_reviewed: StrictBool=False

    @field_validator('speaker_ref')
    @classmethod
    def reference(cls,v):return SubscriptionPreference.canonical_subscriber(v)

    @field_validator('attribution')
    @classmethod
    def label(cls,v):return text(v)


class Event(Fixture):
    event_ref: str = Field(min_length=3,max_length=96)
    revision: int = Field(strict=True,ge=0,le=100000)
    kind: Literal['event','webinar']
    title: str = Field(min_length=1,max_length=200)
    description: str = Field(min_length=1,max_length=1000)
    canonical_url: str = Field(min_length=10,max_length=500)
    starts_at: datetime
    ends_at: datetime
    updated_at: datetime
    timezone_name: str = Field(min_length=1,max_length=64)
    lifecycle: Literal['draft','scheduled','completed','cancelled']='draft'
    change_notice: str | None = Field(default=None,min_length=1,max_length=400)
    source_refs: list[str] = Field(min_length=1,max_length=20)
    speakers: list[Speaker] = Field(min_length=1,max_length=20)
    editorial_reviewed: StrictBool=False
    rights_reviewed: StrictBool=False
    privacy_reviewed: StrictBool=False
    suppressed: StrictBool=False

    @field_validator('event_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('title','description','change_notice')
    @classmethod
    def label(cls,v):return text(v) if v is not None else None

    @field_validator('canonical_url')
    @classmethod
    def url(cls,v):return public_url(v)

    @field_validator('starts_at','ends_at','updated_at')
    @classmethod
    def aware(cls,v):
        if v.tzinfo is None or v.utcoffset() is None or v.microsecond:
            raise ValueError('Explicit timezone and whole seconds required')
        if not 1900<=v.year<=2200:raise ValueError('Bounded event year required')
        return v

    @field_validator('timezone_name')
    @classmethod
    def zone(cls,v):
        try:ZoneInfo(v)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('Known IANA timezone required') from None
        return v

    @field_validator('source_refs')
    @classmethod
    def sources(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Duplicate source')
        return [opaque(x) for x in v]

    @model_validator(mode='after')
    def schedule(self):
        if self.ends_at.astimezone(timezone.utc)<=self.starts_at.astimezone(timezone.utc):raise ValueError('Positive duration required')
        zone=ZoneInfo(self.timezone_name)
        for moment in (self.starts_at,self.ends_at):
            local=moment.astimezone(zone)
            if local.replace(tzinfo=None)!=moment.replace(tzinfo=None) or local.utcoffset()!=moment.utcoffset():
                raise ValueError('Local time and offset must match timezone rules')
        if (self.revision>0 or self.lifecycle=='cancelled') and not self.change_notice:
            raise ValueError('Update or cancellation notice required')
        if self.lifecycle=='cancelled' and self.revision==0:raise ValueError('Cancellation must advance revision')
        if len({s.speaker_ref for s in self.speakers})!=len(self.speakers):raise ValueError('Duplicate speaker')
        if any(s.organization_id!=self.organization_id for s in self.speakers):raise ValueError('Cross-tenant speaker')
        return self


def escaped(value):
    return value.replace('\\','\\\\').replace(';',r'\;').replace(',',r'\,')


def folded(line):
    """Fold by UTF-8 octets without splitting a Unicode character."""
    parts=[];current=''
    for char in line:
        if len((current+char).encode('utf-8'))>75:
            parts.append(current);current=' '
        current+=char
    return '\r\n'.join([*parts,current])


def preview_event(event:Event,tenant:str):
    if event.organization_id!=tenant:raise ValueError('Tenant mismatch')
    reviewed=event.editorial_reviewed and event.rights_reviewed and event.privacy_reviewed and all(s.privacy_reviewed and s.attribution_reviewed for s in event.speakers)
    eligible=reviewed and not event.suppressed and event.lifecycle!='draft'
    uid=hashlib.sha256((tenant+'\0'+event.event_ref).encode()).hexdigest()+'@synthetic.invalid'
    stamp=lambda dt:dt.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    status='CANCELLED' if event.lifecycle=='cancelled' else 'CONFIRMED'
    description=event.description+' | Speakers: '+'; '.join(s.attribution for s in event.speakers)
    if event.change_notice:description+=' | Notice: '+event.change_notice
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//SCEC//Synthetic Offline Preview 11.6//EN','CALSCALE:GREGORIAN','BEGIN:VEVENT',
           'UID:'+uid,'DTSTAMP:'+stamp(event.updated_at),'LAST-MODIFIED:'+stamp(event.updated_at),'SEQUENCE:'+str(event.revision),
           'DTSTART:'+stamp(event.starts_at),'DTEND:'+stamp(event.ends_at),'STATUS:'+status,
           'SUMMARY:'+escaped(event.title),'DESCRIPTION:'+escaped(description),'URL:'+event.canonical_url,
           'END:VEVENT','END:VCALENDAR']
    normalized=event.model_dump(mode='json');normalized['source_refs'].sort()
    for field in ('starts_at','ends_at','updated_at'):normalized[field]=getattr(event,field).isoformat()
    return seal({'mode':'offline-synthetic-event-preview','fixture':normalized,'event_uid':uid,'review_complete_for_preview_only':reviewed,
                 'ics_preview':'\r\n'.join(folded(line) for line in lines)+'\r\n' if eligible else None,
                 'calendar_writes_enabled':False,'registration_capture_enabled':False,'invitations_enabled':False,
                 'timezone_validation':'host-IANA-rules-offset-match; UTC-export; no timezone ownership claim'},tenant,'11.6.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-synthetic-event-preview','calendar_writes_enabled':False,'registration_capture_enabled':False},str(tenant),'11.6.0')


@router.post('/preview')
def preview(payload:Event,tenant=Depends(_scope)):
    try:return preview_event(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/register')
@router.post('/invite')
@router.post('/broadcast')
@router.post('/write-calendar')
@router.post('/publish')
@router.post('/send')
@router.post('/schedule')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live event operations disabled')
