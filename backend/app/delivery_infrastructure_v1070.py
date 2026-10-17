"""v10.7 delivery infrastructure: synthetic, no transport adapters or side effects."""
import hashlib
import json
import os
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .wordpress_bridge_certification_v1050 import DANGER_FLAGS

router = APIRouter(prefix='/v1/delivery-infrastructure', tags=['delivery-staging'])
CHANNELS = ('email', 'in-app', 'sms')
GATES = ('live_consent_evidence', 'verified_recipient', 'suppression_registry', 'unsubscribe_enforcement',
         'template_security_review', 'human_dispatch_approval', 'transport_provider_review',
         'retry_idempotency_validation', 'production_acceptance')
RETRY_SECONDS = (60, 300, 1800)

class DeliveryPreview(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reference: str = Field(min_length=3, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    channel: Literal['email','in-app','sms']
    template: Literal['acknowledgment','case-update','review-request','follow-up','status-notice']
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r'^[A-Za-z0-9_.:-]+$')
    recipient_verified: bool = False
    consent_recorded: bool = False
    consent_channel: Literal['email','in-app','sms','none'] = 'none'
    suppressed: bool = False
    unsubscribed: bool = False
    human_approval_recorded: bool = False
    contains_sensitive_content: bool = False
    simulated_retry_attempt: int = Field(default=0, ge=0, le=4)

def delivery_assessment(payload: DeliveryPreview, organization_id: str) -> dict:
    tenant = str(UUID(organization_id))
    if tenant != organization_id: raise ValueError('Noncanonical tenant ID')
    blockers = []
    if not payload.recipient_verified: blockers.append('recipient-unverified')
    if not payload.consent_recorded or payload.consent_channel != payload.channel: blockers.append('channel-consent-not-proven')
    if payload.suppressed: blockers.append('suppressed')
    if payload.unsubscribed: blockers.append('unsubscribed')
    if not payload.human_approval_recorded: blockers.append('human-approval-missing')
    if payload.contains_sensitive_content: blockers.append('sensitive-content-review')
    if payload.simulated_retry_attempt > 3: blockers.append('retry-budget-exhausted')
    # Hash only synthetic tokens; never accept or include recipient addresses, message bodies, or PII.
    digest = hashlib.sha256(json.dumps({'tenant':tenant, 'reference':payload.reference,
            'channel':payload.channel,'template':payload.template,'key':payload.idempotency_key},
            sort_keys=True, separators=(',',':')).encode()).hexdigest()
    result = {'release':'10.7.0', 'organization_id':tenant, 'channel':payload.channel,
        'template':payload.template, 'synthetic_evidence_sha256':digest, 'blockers':blockers,
        'eligible_for_human_review':not blockers, 'next_retry_delay_seconds_preview':(
          RETRY_SECONDS[payload.simulated_retry_attempt] if payload.simulated_retry_attempt < 3 else None),
        'requires_human_approval':True,'production_certified':False,
        'delivery_authorized':False,'messages_sent':0,'queued':False,'persisted':False,
        'outbound_enabled':False,'federated':False,'deleted':False,
        'transport_adapters':[], 'suppression_registry_connected':False,
        'unsubscribe_registry_connected':False}
    return result

def safety_state() -> bool:
    return all(os.getenv(flag,'0') == '0' for flag in DANGER_FLAGS)

def _scope(x_scec_organization_id: str | None = Header(default=None), actor: Principal | None = Depends(principal)):
    if os.getenv('SCEC_DELIVERY_STAGING_ENABLED','0') != '1' or not safety_state():
        raise HTTPException(503,'Delivery staging disabled')
    if not bound_mode(): raise HTTPException(503,'Bound service identity required')
    tenant = tenant_for_principal(x_scec_organization_id,actor)
    allowed = {v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(tenant) not in allowed: raise HTTPException(403,'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator','service'}): raise HTTPException(403,'Privileged role required')
    return tenant

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'10.7.0','organization_id':str(tenant),'mode':'synthetic-preview-only',
      'production_certified':False,'outbound_enabled':False,'transport_adapters':[],
      'queued':False,'pending_live_gates':list(GATES)}

@router.get('/contracts')
def contracts(tenant=Depends(_scope)):
    return {'release':'10.7.0','organization_id':str(tenant),'channels':list(CHANNELS),
        'retry_seconds_preview':list(RETRY_SECONDS),'transport_adapters':[],
        'suppression_and_unsubscribe':'caller-supplied-synthetic-flags-only',
        'real_recipient_lookup':False,'persistence':False,'delivery':False}

@router.post('/preview')
def preview(payload:DeliveryPreview,tenant=Depends(_scope)):
    try: return delivery_assessment(payload,str(tenant))
    except ValueError as err: raise HTTPException(422,str(err)) from err

@router.post('/send')
@router.post('/dispatch')
@router.post('/enqueue')
@router.post('/retry')
@router.post('/approve')
@router.post('/commit')
@router.post('/promote')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Outbound delivery, queueing, approval, persistence and promotion disabled')
