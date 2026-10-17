"""v10.8.0 - deterministic synthetic reliability assessments; never monitors or changes live state."""
import hashlib
import json
import os
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .wordpress_bridge_certification_v1050 import DANGER_FLAGS

router = APIRouter(prefix='/v1/observability-reliability', tags=['observability-staging'])
FAILURES = ('none','transient-network','timeout','rate-limited','dependency-down','invalid-contract','authorization-denied','integrity-failure')
SEVERITIES = ('info','warning','critical')
RECOVERY_STEPS = ('isolate', 'investigate', 'human-review', 'retest', 'document')
LIVE_GATES = ('approved_log_redaction', 'tenant_scope_verified', 'monitoring_retention_policy',
              'alert_routing_review', 'incident_response_runbook', 'backup_restore_exercise',
              'production_acceptance')
RETRY_SECONDS = (60, 300, 1800)

class ReliabilityScenario(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    reference: str = Field(min_length=3, max_length=64, pattern=r'^[A-Za-z0-9_.:-]+$')
    incident_key: str = Field(min_length=8, max_length=80, pattern=r'^[A-Za-z0-9_.:-]+$')
    component: Literal['backend','wordpress-bridge','independent-web','persistence','delivery']
    failure: Literal['none','transient-network','timeout','rate-limited','dependency-down','invalid-contract','authorization-denied','integrity-failure']
    attempt: int = Field(default=0, ge=0, le=5)
    synthetic_observed_seconds: int = Field(default=0, ge=0, le=3600)
    synthetic_affected_count: int = Field(default=0, ge=0, le=10000)
    human_review_acknowledged: bool = False

def assess(scenario:ReliabilityScenario, organization_id:str) -> dict:
    tenant = str(UUID(organization_id))
    if tenant != organization_id: raise ValueError('Noncanonical tenant ID')
    retryable = scenario.failure in ('transient-network','timeout','rate-limited','dependency-down')
    critical = scenario.failure in ('authorization-denied','integrity-failure')
    severity = ('critical' if critical else 'warning' if scenario.failure != 'none' else 'info')
    delay = RETRY_SECONDS[scenario.attempt] if retryable and scenario.attempt < len(RETRY_SECONDS) else None
    if scenario.failure == 'none': action = 'no-action'
    elif critical: action = 'human-incident-escalation'
    elif retryable and delay is not None: action = 'simulate-retry-only'
    else: action = 'human-triage'
    evidence = hashlib.sha256(json.dumps({'tenant':tenant,'reference':scenario.reference,
        'incident_key':scenario.incident_key,'component':scenario.component,'failure':scenario.failure,
        'attempt':scenario.attempt},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {'release':'10.8.0','organization_id':tenant,'component':scenario.component,
        'failure_class':scenario.failure,'severity':severity,'suggested_action_preview':action,
        'retry_delay_seconds_preview':delay,'synthetic_evidence_sha256':evidence,
        'synthetic_observed_seconds':scenario.synthetic_observed_seconds,
        'synthetic_affected_count':scenario.synthetic_affected_count,
        'human_review_acknowledged':scenario.human_review_acknowledged,
        'recovery_steps_preview':list(RECOVERY_STEPS),'telemetry_source':'caller-supplied-synthetic-only',
        'live_metrics_collected':False,'live_logs_collected':False,'alerts_sent':False,
        'retries_executed':0,'recovery_executed':False,'incident_created':False,
        'backup_restored':False,'production_certified':False,'production_writes_enabled':False,
        'outbound_enabled':False,'human_login_enabled':False,'deleted':False,'federated':False,
        'persisted':False,'eligible_for_production_promotion':False}

def safety_state() -> bool:
    return all(os.getenv(flag,'0') == '0' for flag in DANGER_FLAGS)

def _scope(x_scec_organization_id:str|None=Header(default=None), actor:Principal|None=Depends(principal)):
    if os.getenv('SCEC_RELIABILITY_STAGING_ENABLED','0') != '1' or not safety_state():
        raise HTTPException(503,'Reliability staging disabled')
    if not bound_mode():raise HTTPException(503,'Bound service identity required')
    tenant=tenant_for_principal(x_scec_organization_id,actor)
    allowed={v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}
    if str(tenant) not in allowed:raise HTTPException(403,'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator','service'}):raise HTTPException(403,'Privileged role required')
    return tenant

@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'10.8.0','organization_id':str(tenant),'mode':'synthetic-assessment-only',
        'live_metrics_collected':False,'alerts_sent':False,'recovery_executed':False,
        'production_certified':False,'pending_live_gates':list(LIVE_GATES)}

@router.get('/contracts')
def contracts(tenant=Depends(_scope)):
    return {'release':'10.8.0','organization_id':str(tenant),'failure_classes':list(FAILURES),
        'severities':list(SEVERITIES),'retry_seconds_preview':list(RETRY_SECONDS),
        'telemetry':'synthetic-request-only','live_metrics_collected':False,'production_certified':False}

@router.post('/assess')
def assess_endpoint(payload:ReliabilityScenario,tenant=Depends(_scope)):
    try:return assess(payload,str(tenant))
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc

@router.post('/collect')
@router.post('/alert')
@router.post('/retry')
@router.post('/recover')
@router.post('/restore')
@router.post('/create-incident')
@router.post('/promote')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live telemetry, incident writes, alerts, recovery and promotion disabled')
