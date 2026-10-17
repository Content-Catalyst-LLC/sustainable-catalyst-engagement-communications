"""Staging-only, deterministic RSS 2.0, Atom 1.0 and JSON Feed 1.1 previews.

Only caller-supplied synthetic public metadata; no fetching, storage or publication.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from email.utils import format_datetime
from uuid import UUID
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .research_distribution_v1100 import _scope
from .production_acceptance_v1090 import GATES as LIVE_GATES

router=APIRouter(prefix='/v1/research-feeds',tags=['research-feeds-staging'])
FORMATS=('rss','atom','json-feed')
BLOCKED_ACTIONS=('publish','syndicate','enqueue','send','activate','federate','delete')
ATOM='http://www.w3.org/2005/Atom'

def valid_url(value):
    parsed=urlsplit(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None,443):
        raise ValueError('Canonical URLs must be HTTPS without userinfo, fragments, or nonstandard ports')
    if parsed.hostname in ('localhost','127.0.0.1','0.0.0.0') or parsed.hostname.endswith(('.local','.internal')):
        raise ValueError('Nonpublic host is not allowed')
    return value

class FeedEntry(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    object_ref:str=Field(min_length=3,max_length=96,pattern=r'^[A-Za-z0-9_.:-]+$')
    revision:str=Field(min_length=1,max_length=48,pattern=r'^[A-Za-z0-9_.:-]+$')
    title:str=Field(min_length=1,max_length=180)
    summary:str=Field(min_length=1,max_length=500)
    canonical_url:str=Field(max_length=300)
    updated_at:datetime
    source_refs:list[str]=Field(min_length=1,max_length=12)
    rights_reviewed:bool=False
    editorial_reviewed:bool=False
    privacy_reviewed:bool=False
    distribution_approved:bool=False

    @field_validator('canonical_url')
    @classmethod
    def check_url(cls,v):return valid_url(v)

    @field_validator('updated_at')
    @classmethod
    def aware_date(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('Timezone offset required')
        return v

    @field_validator('source_refs')
    @classmethod
    def opaque_refs(cls,v):
        if len(v)!=len(set(v)) or any(not re.fullmatch(r'[A-Za-z0-9_.:-]{3,96}',s) for s in v):
            raise ValueError('Source references must be unique opaque IDs')
        return v

class FeedPreview(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    format:Literal['rss','atom','json-feed']
    feed_title:str=Field(min_length=1,max_length=180)
    feed_description:str=Field(min_length=1,max_length=500)
    home_url:str=Field(max_length=300)
    feed_url:str=Field(max_length=300)
    entries:list[FeedEntry]=Field(min_length=1,max_length=20)

    @field_validator('home_url','feed_url')
    @classmethod
    def check_url(cls,v):return valid_url(v)

    @model_validator(mode='after')
    def no_duplicate_refs(self):
        refs=[(e.object_ref,e.revision) for e in self.entries]
        if len(refs)!=len(set(refs)):raise ValueError('Repeated object revision')
        return self

def canonical_time(dt):return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def ordered_entries(entries):return sorted(entries,key=lambda x:(x.object_ref,x.revision))

def render(payload:FeedPreview,organization_id:str)->dict:
    tenant=str(UUID(organization_id))
    if tenant!=organization_id:raise ValueError('Noncanonical organization id')
    entries=ordered_entries(payload.entries)
    # Canonicalization is stable under input reordering, but source metadata remains visible.
    reviewed=all(e.rights_reviewed and e.editorial_reviewed and e.privacy_reviewed and e.distribution_approved for e in entries)
    def identity(e):return f'{tenant}:{e.object_ref}:{e.revision}'
    if payload.format=='rss':
        root=ET.Element('rss',version='2.0');channel=ET.SubElement(root,'channel')
        for k,v in (('title',payload.feed_title),('link',payload.home_url),('description',payload.feed_description)):
            ET.SubElement(channel,k).text=v
        for e in entries:
            item=ET.SubElement(channel,'item')
            for k,v in (('guid',identity(e)),('title',e.title),('link',e.canonical_url),('description',e.summary),('pubDate',format_datetime(e.updated_at.astimezone(timezone.utc))),('source',','.join(sorted(e.source_refs)))):
                ET.SubElement(item,k).text=v
        media_type='application/rss+xml';text=ET.tostring(root,encoding='unicode')
    elif payload.format=='atom':
        ET.register_namespace('',ATOM)
        root=ET.Element('{%s}feed'%ATOM)
        for k,v in (('id',payload.feed_url),('title',payload.feed_title),('subtitle',payload.feed_description),('updated',max(canonical_time(e.updated_at) for e in entries))):
            ET.SubElement(root,'{%s}%s'%(ATOM,k)).text=v
        ET.SubElement(root,'{%s}link'%ATOM,{'href':payload.feed_url,'rel':'self'})
        for e in entries:
            item=ET.SubElement(root,'{%s}entry'%ATOM)
            for k,v in (('id',identity(e)),('title',e.title),('summary',e.summary),('updated',canonical_time(e.updated_at)),('rights',','.join(sorted(e.source_refs)))):
                ET.SubElement(item,'{%s}%s'%(ATOM,k)).text=v
            ET.SubElement(item,'{%s}link'%ATOM,{'href':e.canonical_url,'rel':'alternate'})
        media_type='application/atom+xml';text=ET.tostring(root,encoding='unicode')
    else:
        doc={'version':'https://jsonfeed.org/version/1.1','title':payload.feed_title,'description':payload.feed_description,'home_page_url':payload.home_url,'feed_url':payload.feed_url,'items':[
            {'id':identity(e),'url':e.canonical_url,'title':e.title,'summary':e.summary,'date_modified':canonical_time(e.updated_at),'_source_refs':sorted(e.source_refs)} for e in entries]}
        media_type='application/feed+json';text=json.dumps(doc,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    return {'release':'11.1.0','organization_id':tenant,'format':payload.format,'media_type':media_type,
            'content_preview':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'entry_count':len(entries),
            'human_review_complete':reviewed,'publication_authorized':False,'actual_syndication_enabled':False,
            'outbound_communications_enabled':False,'persisted':False,'source_fetch_performed':False,
            'federation_enabled':False,'production_certified':False,'live_acceptance_gates_pending':list(LIVE_GATES)}

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'11.1.0','formats':FORMATS,'mode':'synthetic-preview-only','organization_id':str(tenant),
            'production_certified':False,'syndication_enabled':False}

@router.post('/preview')
def feed_preview(payload:FeedPreview,tenant=Depends(_scope)):
    try:return render(payload,str(tenant))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/publish')
@router.post('/syndicate')
@router.post('/enqueue')
@router.post('/send')
@router.post('/activate')
@router.post('/federate')
@router.post('/delete')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live distribution actions disabled')
