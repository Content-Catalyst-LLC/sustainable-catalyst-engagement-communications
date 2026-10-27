"""Authenticated versioned embed contracts; never serves public HTML or CORS."""
import hashlib
import html
import json
import os
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field, StrictBool, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque
from .citation_discovery_v1150 import text, public_url
from .offline_staging import scope, seal

PREFIX='/v1/research-embeds'
SCHEMA='scec.distribution-preview/1'
router=APIRouter(prefix=PREFIX,tags=['embed-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_EMBEDS_STAGING_ENABLED')
BLOCKED_ACTIONS=('publish','serve-public','enable-cors','activate','send','federate','delete')
API_HEADERS={'Cache-Control':'no-store, private','Pragma':'no-cache','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",'X-Frame-Options':'DENY','Vary':'Authorization, Origin, X-SCEC-Organization-ID'}


def origin(value):
    public_url(value)
    p=urlsplit(value)
    if p.path or p.query or p.fragment or p.netloc!=p.hostname:
        raise ValueError('Canonical HTTPS origin without port or path required')
    return value


def allowed_origins():
    values=os.getenv('SCEC_EMBED_ALLOWED_ORIGINS','').split(',')
    try:
        if not values or any(not x.strip() for x in values):raise ValueError('Missing policy')
        result=tuple(sorted({origin(x.strip()) for x in values}))
        if len(result)>10:raise ValueError('Policy bound exceeded')
        return result
    except ValueError:raise HTTPException(503,'Embed origin policy unavailable') from None


class Embed(Fixture):
    schema_version: Literal['scec.distribution-preview/1']=SCHEMA
    object_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    title: str = Field(min_length=1,max_length=180)
    summary: str = Field(min_length=1,max_length=600)
    canonical_url: str = Field(min_length=10,max_length=500)
    requested_origin: str = Field(min_length=10,max_length=200)
    source_refs: list[str] = Field(min_length=1,max_length=12)
    updated_at: datetime
    expires_at: datetime
    as_of: datetime
    state: Literal['active','corrected','retracted','withdrawn']='active'
    notice: str | None = Field(default=None,min_length=1,max_length=300)
    notice_source_ref: str | None = Field(default=None,min_length=3,max_length=96)
    rights_reviewed: StrictBool=False
    editorial_reviewed: StrictBool=False
    privacy_reviewed: StrictBool=False
    distribution_reviewed: StrictBool=False
    suppressed: StrictBool=False

    @field_validator('object_ref','notice_source_ref')
    @classmethod
    def reference(cls,v):return opaque(v) if v is not None else None

    @field_validator('title','summary','notice')
    @classmethod
    def label(cls,v):return text(v) if v is not None else None

    @field_validator('canonical_url')
    @classmethod
    def url(cls,v):return public_url(v)

    @field_validator('requested_origin')
    @classmethod
    def host(cls,v):return origin(v)

    @field_validator('source_refs')
    @classmethod
    def sources(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Duplicate source')
        return [opaque(x) for x in v]

    @field_validator('updated_at','expires_at','as_of')
    @classmethod
    def aware(cls,v):
        if v.tzinfo is None or v.utcoffset() is None:raise ValueError('Timezone required')
        return v

    @model_validator(mode='after')
    def provenance(self):
        if self.expires_at<=self.updated_at:raise ValueError('Positive validity interval required')
        if self.state!='active' and (not self.notice or not self.notice_source_ref):raise ValueError('Sourced notice required')
        if self.notice_source_ref and self.notice_source_ref not in self.source_refs:raise ValueError('Unknown notice source')
        return self


def render_embed(payload:Embed,tenant:str,policy):
    if payload.organization_id!=tenant:raise ValueError('Tenant mismatch')
    accepted=tuple(sorted({origin(x) for x in policy}))
    if payload.requested_origin not in accepted:raise PermissionError('Origin denied')
    normalized=payload.model_dump(mode='json');normalized['source_refs'].sort()
    for field in ('updated_at','expires_at','as_of'):normalized[field]=getattr(payload,field).astimezone(timezone.utc).isoformat()
    input_hash=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    reasons=[]
    if not all(getattr(payload,k) for k in ('rights_reviewed','editorial_reviewed','privacy_reviewed','distribution_reviewed')):reasons.append('review-required')
    if payload.suppressed:reasons.append('suppressed')
    if payload.state in ('retracted','withdrawn'):reasons.append(payload.state)
    if payload.as_of<payload.updated_at:reasons.append('not-yet-current')
    if payload.as_of>=payload.expires_at:reasons.append('expired')
    content=None
    if not reasons:
        content={'title':payload.title,'summary':payload.summary,'canonical_url':payload.canonical_url,'source_refs':sorted(payload.source_refs),'notice':payload.notice,'notice_source_ref':payload.notice_source_ref}
    markup=None
    if content:
        markup='<article><h1>'+html.escape(payload.title)+'</h1><p>'+html.escape(payload.summary)+'</p>'
        if payload.notice:markup+='<p>'+html.escape(payload.notice)+'</p>'
        markup+='<a rel="noreferrer noopener" href="'+html.escape(payload.canonical_url,quote=True)+'">Canonical source</a></article>'
    csp="default-src 'none'; base-uri 'none'; form-action 'none'; sandbox; frame-ancestors "+payload.requested_origin
    return seal({'mode':'offline-synthetic-embed-contract','schema_version':SCHEMA,'object_ref':payload.object_ref,'revision':payload.revision,
                 'input_sha256':input_hash,'configured_origins_sha256':hashlib.sha256(json.dumps(accepted).encode()).hexdigest(),
                 'requested_origin':payload.requested_origin,'withheld_reasons':reasons,'content':content,'html_fragment_preview':markup,
                 'required_future_html_headers':{'Content-Security-Policy':csp,'Cache-Control':'no-store, private','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'},
                 'public_embed_serving_enabled':False,'cors_enabled':False,'remote_resources_enabled':False},tenant,'11.8.0')


def install_headers(app):
    @app.middleware('http')
    async def embed_headers(request:Request,call_next):
        response=await call_next(request)
        if request.url.path==PREFIX or request.url.path.startswith(PREFIX+'/'):
            for key,value in API_HEADERS.items():response.headers[key]=value
        return response


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-synthetic-embed-contract','schema_version':SCHEMA,'public_embed_serving_enabled':False,'cors_enabled':False},str(tenant),'11.8.0')


@router.post('/preview')
def preview(payload:Embed,request:Request,tenant=Depends(_scope)):
    policy=allowed_origins()
    if request.headers.get('origin') not in (None,payload.requested_origin):raise HTTPException(403,'Origin denied')
    try:return render_embed(payload,str(tenant),policy)
    except PermissionError:raise HTTPException(403,'Origin denied') from None
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/publish')
@router.post('/serve-public')
@router.post('/enable-cors')
@router.post('/activate')
@router.post('/send')
@router.post('/federate')
@router.post('/delete')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Public embed operations disabled')
