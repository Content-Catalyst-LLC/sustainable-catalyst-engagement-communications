"""v9.5: authenticated, scoped, non-persistent notification planning. No transport integration."""
import os
from collections import Counter
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, bound_mode, principal, tenant_for_principal

router=APIRouter(prefix="/v1/communications-intelligence",tags=["communications-staging"])
EVENTS={"contact-received","feedback-received","feature-review","support-update","advisory-inquiry","channel-update"}
CHANNELS={"email","in-app","sms"}
TEMPLATES={"acknowledgment","case-update","review-request","follow-up","status-notice"}
class NotificationPlan(BaseModel):
    model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
    event_type:str=Field(min_length=3,max_length=48)
    template:str=Field(min_length=3,max_length=48)
    requested_channels:list[str]=Field(min_length=1,max_length=3)
    consent_recorded:bool=False
    consent_scope:list[str]=Field(default_factory=list,max_length=3)
    recipient_verified:bool=False
    essential_service_notice:bool=False
    escalation_requested:bool=False
    sensitive_content:bool=False
    reference:str=Field(default="staging-case",min_length=3,max_length=64)

class NotificationBatch(BaseModel):
    model_config=ConfigDict(extra="forbid")
    plans:list[NotificationPlan]=Field(min_length=1,max_length=25)

def scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal))->UUID:
    if os.getenv('SCEC_COMMUNICATIONS_STAGING_ENABLED','0')!='1':raise HTTPException(503,'Communications staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound identity required')
    org=tenant_for_principal(x_scec_organization_id,actor)
    allowed={x.strip() for x in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if x.strip()}
    if str(org) not in allowed:raise HTTPException(403,'Organization not allowlisted')
    if not actor.roles.intersection({'administrator','advisor'}):raise HTTPException(403,'Communications role required')
    return org

def evaluate(plan:NotificationPlan)->dict:
    reasons=[]
    if plan.event_type not in EVENTS: reasons.append('unsupported-event')
    if plan.template not in TEMPLATES: reasons.append('unsupported-template')
    if len(set(plan.requested_channels)) != len(plan.requested_channels):reasons.append('duplicate-channels')
    if any(ch not in CHANNELS for ch in plan.requested_channels):reasons.append('unsupported-channel')
    if any(ch not in CHANNELS for ch in plan.consent_scope):reasons.append('invalid-consent-scope')
    if not plan.recipient_verified:reasons.append('recipient-verification-required')
    if not plan.consent_recorded:reasons.append('consent-required')
    if not set(plan.requested_channels).issubset(set(plan.consent_scope)): reasons.append('channel-consent-missing')
    if plan.sensitive_content:reasons.append('sensitive-content-review')
    if plan.escalation_requested:reasons.append('human-escalation-review')
    # Even an eligible plan is NEVER authorized for delivery in this version.
    return {'eligible_for_human_review':not reasons,'reasons':reasons,
            'requested_channels':sorted(set(plan.requested_channels)),
            'requires_human_approval':True,'delivery_authorized':False,
            'messages_sent':0,'queued':False,'persisted':False}

@router.get('/status')
def status(org:UUID=Depends(scope)):
    return {'version':'9.5.0','organization_id':str(org),'preview_only':True,
            'writes_enabled':False,'outbound_enabled':False,'transport_adapters':[],
            'wordpress_bridge':'unchanged'}

@router.post('/plan-preview')
def plan_preview(payload:NotificationPlan,org:UUID=Depends(scope)):
    return {'version':'9.5.0','organization_id':str(org),'preview_only':True,'analysis':evaluate(payload)}

@router.post('/audit-preview')
def audit_preview(payload:NotificationBatch,org:UUID=Depends(scope)):
    analyses=[evaluate(p) for p in payload.plans]
    return {'version':'9.5.0','organization_id':str(org),'preview_only':True,'persisted':False,
            'sent':0,'queued':0,'count':len(analyses),
            'event_counts':dict(Counter(p.event_type for p in payload.plans)),
            'review_counts':dict(Counter('eligible' if p['eligible_for_human_review'] else 'blocked' for p in analyses)),
            'reason_counts':dict(Counter(x for item in analyses for x in item['reasons']))}

@router.post('/send')
def send_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Outbound delivery disabled in v9.5.0')

@router.post('/commit')
def commit_disabled(org:UUID=Depends(scope)):
    raise HTTPException(503,'Communications persistence disabled in v9.5.0')
