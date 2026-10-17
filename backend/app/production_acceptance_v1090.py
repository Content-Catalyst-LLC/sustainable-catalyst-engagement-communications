"""v10.9.0: synthetic source-evidence acceptance ledger; all live gates remain unresolved."""
import hashlib
import json
import os
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .wordpress_bridge_certification_v1050 import DANGER_FLAGS

router = APIRouter(prefix='/v1/production-acceptance', tags=['acceptance-staging'])
GATES = (
    'public_https_dns_tls',
    'wordpress_public_launcher_acceptance',
    'authenticated_human_session',
    'csrf_revocation_session_expiry',
    'live_tenant_isolation_roles',
    'privacy_retention_policy',
    'staged_persistence_write_certification',
)
RELEASES = tuple(f'10.{i}.0' for i in range(10))
PROTECTED = ('contact', 'feedback', 'feature-suggestions', 'channel', 'support')
BLOCKED_ACTIONS = ('enable-production-writes','enable-outbound','enable-human-login',
                   'delete-records','enable-federation','promote','certify-live-gates')

class EvidencePreview(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reference: str = Field(min_length=3, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    evidence_key: str = Field(min_length=8, max_length=80, pattern=r'^[A-Za-z0-9_.:-]+$')
    claimed_gate: Literal[
        'public_https_dns_tls','wordpress_public_launcher_acceptance',
        'authenticated_human_session','csrf_revocation_session_expiry',
        'live_tenant_isolation_roles','privacy_retention_policy',
        'staged_persistence_write_certification']
    evidence_kind: Literal['source-preflight','synthetic-test','local-smoke-test','human-review-required']
    review_acknowledged: bool = False

def acceptance_report(*, source_preflight_passed:bool=False) -> dict:
    return {
        'release':'10.9.0',
        'phase':'source-and-staging-acceptance-only',
        'source_preflight_passed':bool(source_preflight_passed),
        'prior_release_lineage':list(RELEASES),
        'protected_wordpress_destinations':list(PROTECTED),
        'live_checks':{},
        'gate_states':{name:'pending-live-evidence' for name in GATES},
        'gates_not_certified':list(GATES),
        'production_certified':False,
        'production_writes_enabled':False,
        'outbound_communications_enabled':False,
        'human_login_enabled':False,
        'deletion_enabled':False,
        'federation_enabled':False,
        'automatic_promotion_enabled':False,
        'production_approval_granted':False,
        'needs_separate_human_live_acceptance':True,
    }

def preview(payload:EvidencePreview, organization_id:str) -> dict:
    tenant = str(UUID(organization_id))
    if tenant != organization_id: raise ValueError('Noncanonical tenant ID')
    raw=json.dumps({'tenant':tenant,'reference':payload.reference,
        'evidence_key':payload.evidence_key,'gate':payload.claimed_gate,
        'kind':payload.evidence_kind},sort_keys=True,separators=(',',':')).encode()
    report=acceptance_report()
    report.update(organization_id=tenant, claimed_gate=payload.claimed_gate,
        evidence_kind=payload.evidence_kind, review_acknowledged=payload.review_acknowledged,
        synthetic_evidence_sha256=hashlib.sha256(raw).hexdigest(),
        evidence_source='request-supplied-synthetic-only',
        evidence_persisted=False, evidence_verified_against_live_system=False,
        gate_certified=False, human_approval_executed=False)
    return report

def safety_state() -> bool:
    return all(os.getenv(flag,'0')=='0' for flag in DANGER_FLAGS)

def _scope(x_scec_organization_id:str|None=Header(default=None),actor:Principal|None=Depends(principal)):
    if os.getenv('SCEC_ACCEPTANCE_STAGING_ENABLED','0')!='1' or not safety_state():
        raise HTTPException(503,'Acceptance staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound service identity required')
    tenant=tenant_for_principal(x_scec_organization_id,actor)
    allowed={v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(tenant) not in allowed:raise HTTPException(403,'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator','service'}):raise HTTPException(403,'Privileged role required')
    return tenant

@router.get('/status')
def status(tenant=Depends(_scope)):
    return dict(acceptance_report(),organization_id=str(tenant))

@router.get('/gates')
def gates(tenant=Depends(_scope)):
    return {'organization_id':str(tenant),'gates':acceptance_report()['gate_states'],
            'production_certified':False,'live_checks':{}}

@router.post('/evidence-preview')
def evidence_preview(payload:EvidencePreview,tenant=Depends(_scope)):
    try:return preview(payload,str(tenant))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/enable-production-writes')
@router.post('/enable-outbound')
@router.post('/enable-human-login')
@router.post('/delete-records')
@router.post('/enable-federation')
@router.post('/promote')
@router.post('/certify-live-gates')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Production activation and live gate certification disabled')
