"""Staging-only, read-only WordPress intake bridge certification.

No WordPress HTTP calls, page changes, PII capture, persistence or delivery.
Evidence describes local code/contracts only, NOT live WordPress acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .identity import Principal, bound_mode, principal, tenant_for_principal

router = APIRouter(prefix='/v1/wordpress-intake-certification', tags=['wordpress-intake-staging'])
CHANNELS = {
    'contact': ('contact','contact-us'),
    'feedback': ('feedback',),
    'feature-suggestions': ('feature-suggestions',),
    'channel': ('channel',),
    'support': ('support',),
}
GATES = ('five_public_destinations','read_only_launcher','no_wordpress_mutation','tenant_binding','consent_not_inferred','no_pii_echo','no_remote_proxy','commit_denied','production_features_disabled')
DANGER_FLAGS = ('SCEC_HUMAN_AUTH_ENABLED','SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED')

class IntakeBridgeEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind: Literal['contact','feedback','feature-suggestions','channel','support']
    source: Literal['wordpress-public-launcher','synthetic-review']
    page_slug: str = Field(min_length=1,max_length=80,pattern=r'^[a-z0-9-]+$')
    consent_to_contact: bool = False
    reference: str | None = Field(default=None,min_length=1,max_length=120,pattern=r'^[A-Za-z0-9_.:-]+$')
    @field_validator('page_slug')
    @classmethod
    def no_extra_slashes(cls,value):
        if '..' in value:raise ValueError('Invalid page slug')
        return value

def preview_evidence(payload: IntakeBridgeEvidence, organization_id: str):
    tenant = str(UUID(organization_id))
    if tenant != organization_id:raise ValueError('Noncanonical organization')
    if payload.page_slug not in CHANNELS[payload.kind]:raise ValueError('Page does not match intake channel')
    result = {
        'release':'10.5.0','organization_id':tenant,'kind':payload.kind,
        'page_slug':payload.page_slug,'source':payload.source,
        'consent_recorded_for_preview_only':payload.consent_to_contact,
        'persisted':False,'forwarded':False,'wordpress_modified':False,
        'live_page_verified':False,'requires_human_review':True,
    }
    result['evidence_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return result

def source_report(root: Path):
    bridge = (root/'wordpress-bridge/sustainable-catalyst-engagement-communications/sustainable-catalyst-engagement-communications.php').read_text()
    entries = ('Contact','Feedback','Feature Suggestions','Channel','Support')
    checks = {
        'five_public_destinations':all("array('"+title+"'," in bridge for title in entries),
        'read_only_launcher':all(s in bridge for s in ('resolve_public_page','get_page_by_path','get_permalink')),
        'no_wordpress_mutation':not any(s in bridge for s in ('wp_insert_post(', 'wp_update_post(', 'wp_delete_post(', 'wp_redirect(')),
        'no_remote_proxy':not any(s in bridge for s in ('wp_remote_post(', 'wp_remote_request(', 'wp_remote_get(')),
        'no_token_relay':not any(s in bridge for s in ('Authorization:', 'wp_set_auth_cookie(', 'wp_create_nonce(')),
        'no_localhost_app_url':"'localhost'" in bridge and 'FILTER_VALIDATE_IP' in bridge,
    }
    return checks

def safety_state():
    return {key:os.getenv(key,'0')=='0' for key in DANGER_FLAGS}

def _scope(x_scec_organization_id: str | None=Header(default=None), actor: Principal | None=Depends(principal)):
    if os.getenv('SCEC_WORDPRESS_BRIDGE_CERT_STAGING_ENABLED','0')!='1' or not all(safety_state().values()):
        raise HTTPException(503,'WordPress bridge certification staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound service identity required')
    tenant = tenant_for_principal(x_scec_organization_id,actor)
    allowed = {v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(tenant) not in allowed:raise HTTPException(403,'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator','service'}):raise HTTPException(403,'Privileged service role required')
    return tenant

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'10.5.0','organization_id':str(tenant),'certification':'source-only-staging',
            'live_wordpress_certified':False,'production_certified':False,'production_writes_enabled':False,
            'channels':sorted(CHANNELS),'pending_live_gates':list(GATES)}

@router.get('/requirements')
def requirements(tenant=Depends(_scope)):
    return {'release':'10.5.0','organization_id':str(tenant),'gates':list(GATES),'live_checks_performed':False}

@router.post('/preview')
def preview(payload: IntakeBridgeEvidence,tenant=Depends(_scope)):
    try:return preview_evidence(payload,str(tenant))
    except ValueError as err:raise HTTPException(422,str(err)) from err

@router.post('/commit')
@router.post('/certify')
@router.post('/promote')
@router.post('/forward')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'WordPress forwarding, persistence and promotion disabled')
