"""v9.6: scoped, non-persistent, deterministic aggregate-only analytics previews."""
import os
import hashlib
import json
from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router=APIRouter(prefix='/v1/engagement-analytics',tags=['engagement-analytics-staging'])
CHANNELS={'contact','feedback','feature-suggestions','channel','support','institutional','communications'}
STAGES={'received','triaged','in-review','action-needed','resolved','closed'}
CATEGORIES={'general','research','platform','data','access','bug','billing','advisory','other'}
SEVERITIES={'none','low','medium','high','critical'}

class AggregateEvent(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    channel:str
    stage:str='received'
    category:str='general'
    severity:str='none'
    escalation_requested:bool=False
    communication_eligible:bool=False
    occurred_day:str|None=Field(default=None,pattern=r'^\d{4}-\d{2}-\d{2}$')
    @model_validator(mode='after')
    def validate_enum(self):
        for field,options in (('channel',CHANNELS),('stage',STAGES),('category',CATEGORIES),('severity',SEVERITIES)):
            if getattr(self,field) not in options:raise ValueError('Unsupported '+field)
        if self.occurred_day:
            from datetime import date
            try:date.fromisoformat(self.occurred_day)
            except ValueError:raise ValueError('Invalid calendar date')
        return self

class AnalyticsBatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    events:list[AggregateEvent]=Field(min_length=1,max_length=100)


def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv('SCEC_ANALYTICS_STAGING_ENABLED','0')!='1':raise HTTPException(503,'Analytics staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound identity required')
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={x.strip() for x in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if x.strip()}
    if str(org) not in allowed:raise HTTPException(403,'Organization not allowlisted')
    if not actor.roles.intersection({'administrator','advisor'}):raise HTTPException(403,'Analytics role required')
    return org


def aggregate(batch:AnalyticsBatch)->dict:
    events=batch.events
    count=len(events)
    dimensions=('channel','stage','category','severity')
    groups={field:dict(sorted(Counter(getattr(event,field) for event in events).items())) for field in dimensions}
    escalations=sum(event.escalation_requested for event in events)
    eligible=sum(event.communication_eligible for event in events)
    # This is merely analysis of submitted flags; it never implies consent or authorization.
    return {'record_count':count,'counts':groups,'escalation_count':escalations,
            'communication_eligible_flag_count':eligible,
            'communication_eligible_flag_rate':round(eligible/count,4),
            'received_count':groups['stage'].get('received',0),
            'resolved_or_closed_count':groups['stage'].get('resolved',0)+groups['stage'].get('closed',0),
            'classification_method':'bounded supplied-fields aggregation',
            'historical_records_queried':0,'data_source':'request-supplied-only',
            'personal_data_included':False,'persisted':False,'outbound_enabled':False,
            'export_generated':False,'human_review_required':True}

def fingerprint(report:dict)->str:
    return hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@router.get('/status')
def status(org:UUID=Depends(scope)):
    return {'version':'9.6.0','organization_id':str(org),'preview_only':True,
            'writes_enabled':False,'outbound_enabled':False,'data_source':'request-supplied-only',
            'wordpress_bridge':'unchanged','max_events':100}

@router.post('/report-preview')
def report_preview(batch:AnalyticsBatch,org:UUID=Depends(scope)):
    data=aggregate(batch)
    return {'version':'9.6.0','organization_id':str(org),'preview_only':True,
            'report':data,'deterministic_sha256':fingerprint(data)}

@router.post('/funnel-preview')
def funnel_preview(batch:AnalyticsBatch,org:UUID=Depends(scope)):
    data=aggregate(batch)
    return {'version':'9.6.0','organization_id':str(org),'preview_only':True,
            'stages':data['counts']['stage'],'total':data['record_count'],
            'note':'Distribution only; events are not linked trajectories or conversion cohorts.',
            'persisted':False,'outbound_enabled':False}

@router.post('/export')
def export_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Analytics exports disabled in v9.6.0')

@router.post('/commit')
def commit_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Analytics writes disabled in v9.6.0')
