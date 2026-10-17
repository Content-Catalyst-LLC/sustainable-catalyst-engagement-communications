"""v10.6 synthetic privacy, consent and retention readiness; no real data processing."""
import hashlib
import json
import os
from datetime import date, timedelta
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .wordpress_bridge_certification_v1050 import CHANNELS, DANGER_FLAGS

router = APIRouter(prefix='/v1/privacy-consent-retention', tags=['privacy-staging'])
POLICY_VERSION = '10.6.0-draft'
RETENTION = {'contact':90,'feedback':180,'feature-suggestions':180,'channel':90,'support':365}
PURPOSE = {'contact':'respond-to-inquiry','feedback':'evaluate-feedback','feature-suggestions':'evaluate-feature-suggestion','channel':'manage-channel-inquiry','support':'respond-to-support'}
GATES = ('privacy_notice_acceptance','legal_basis_review','live_consent_evidence','data_subject_rights_workflow','retention_schedule_approval','secure_deletion_validation','storage_and_backup_mapping','production_privacy_acceptance')

class PrivacyPreview(BaseModel):
    model_config=ConfigDict(extra='forbid', str_strip_whitespace=True)
    channel: Literal['contact','feedback','feature-suggestions','channel','support']
    page_slug: str = Field(min_length=1,max_length=80,pattern=r'^[a-z0-9-]+$')
    consent_explicit: bool = False
    lawful_basis: Literal['consent','legitimate-interest','contract','not-assessed'] = 'not-assessed'
    simulated_received_date: date
    simulated_as_of: date
    synthetic_reference: str | None = Field(default=None,max_length=64,pattern=r'^[A-Za-z0-9_.:-]+$')

def classify(payload: PrivacyPreview, organization_id: str):
    tenant = str(UUID(organization_id))
    if tenant != organization_id: raise ValueError('Noncanonical tenant ID')
    if payload.page_slug not in CHANNELS[payload.channel]: raise ValueError('Channel/page mismatch')
    if payload.simulated_as_of < payload.simulated_received_date: raise ValueError('Assessment precedes receipt')
    if payload.lawful_basis == 'consent' and not payload.consent_explicit: raise ValueError('Consent basis requires explicit consent evidence')
    if payload.lawful_basis == 'not-assessed' and payload.consent_explicit: raise ValueError('Lawful basis must be assessed; consent checkbox is insufficient')
    days=RETENTION[payload.channel]
    deadline=payload.simulated_received_date + timedelta(days=days)
    result={'release':'10.6.0','policy_version':POLICY_VERSION,'organization_id':tenant,'channel':payload.channel,
      'purpose':PURPOSE[payload.channel],'retention_days_draft':days,'retention_review_date':deadline.isoformat(),
      'retention_review_due':payload.simulated_as_of>=deadline,'consent_explicit_for_preview':payload.consent_explicit,
      'lawful_basis_for_preview':payload.lawful_basis,'production_policy_approved':False,
      'data_subject_verified':False,'personal_data_collected':False,'persisted':False,'deleted':False,
      'outbound_sent':False,'federated':False,'real_retention_executed':False,'human_review_required':True}
    result['evidence_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result

def safety_state():
    return all(os.getenv(flag,'0')=='0' for flag in DANGER_FLAGS)

def _scope(x_scec_organization_id: str|None=Header(default=None), actor: Principal|None=Depends(principal)):
    if os.getenv('SCEC_PRIVACY_RETENTION_STAGING_ENABLED','0')!='1' or not safety_state():
        raise HTTPException(503,'Privacy retention staging disabled')
    if not bound_mode(): raise HTTPException(503,'Bound service identity required')
    tenant=tenant_for_principal(x_scec_organization_id,actor)
    allowed={a.strip() for a in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if a.strip()}
    if str(tenant) not in allowed: raise HTTPException(403,'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator','service'}):raise HTTPException(403,'Privileged service role required')
    return tenant

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'10.6.0','organization_id':str(tenant),'certification':'synthetic-source-staging',
            'production_certified':False,'production_writes_enabled':False,'real_deletion_enabled':False,
            'policy_approved':False,'live_checks_performed':False,'pending_live_gates':list(GATES)}

@router.get('/policy-draft')
def policy_draft(tenant=Depends(_scope)):
    return {'release':'10.6.0','organization_id':str(tenant),'status':'UNAPPROVED_DRAFT',
            'retention_days_by_channel':RETENTION,'purposes_by_channel':PURPOSE,'not_a_legal_determination':True,
            'no_automatic_expiry_or_deletion':True}

@router.post('/preview')
def preview(payload:PrivacyPreview,tenant=Depends(_scope)):
    try:return classify(payload,str(tenant))
    except (ValueError, OverflowError) as err: raise HTTPException(422,str(err)) from err

@router.post('/approve')
@router.post('/delete')
@router.post('/commit')
@router.post('/export')
@router.post('/promote')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Privacy policy approval, deletion, persistence, export and promotion disabled')
