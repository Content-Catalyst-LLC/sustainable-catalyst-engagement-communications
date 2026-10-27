"""Immutable synthetic review records; no live approval or identity role changes."""
import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator, model_validator
from .communication_objects_v1200 import FrozenFixture
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque, SubscriptionPreference
from .rights_suppression_v1230 import PolicySimulation, simulate_policy
from .events_v1160 import Event
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/editorial-workflows',tags=['editorial-workflows-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_WORKFLOWS_STAGING_ENABLED')
ROLES=('editorial','scientific','legal','privacy')
BLOCKED_ACTIONS=('approve-live','change-role','commit','send','publish','activate','delete','federate')


class ReviewFacts(FrozenFixture):
    decision_ref: str = Field(min_length=3,max_length=96)
    reviewer_ref: str = Field(max_length=46)
    role: Literal['editorial','scientific','legal','privacy']
    outcome: Literal['approve','reject','abstain']
    subject_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    subject_revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    decided_at: datetime
    reason_code: Literal['approved-synthetic','needs-revision','source-incomplete','rights-review','privacy-review']

    @field_validator('decision_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('reviewer_ref')
    @classmethod
    def reviewer(cls,v):return SubscriptionPreference.canonical_subscriber(v)

    @field_validator('decided_at')
    @classmethod
    def aware(cls,v):return Event.aware(v).astimezone(timezone.utc)

    @model_validator(mode='after')
    def reason_matches_outcome(self):
        if (self.outcome=='approve')!=(self.reason_code=='approved-synthetic'):raise ValueError('Review outcome and reason conflict')
        return self


def decision_digest(facts:ReviewFacts):
    return hashlib.sha256(json.dumps(facts.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode()).hexdigest()


class ReviewDecision(ReviewFacts):
    record_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def integrity(self):
        facts=ReviewFacts(**self.model_dump(exclude={'record_sha256'}))
        if self.record_sha256!=decision_digest(facts):raise ValueError('Review record integrity mismatch')
        return self


def make_decision(**values):
    facts=ReviewFacts(**values)
    return ReviewDecision(**facts.model_dump(),record_sha256=decision_digest(facts))


class ReviewWorkflow(Fixture):
    workflow_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    author_ref: str = Field(max_length=46)
    policy: PolicySimulation
    policy_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    as_of: datetime
    decisions: tuple[ReviewDecision,...] = Field(default_factory=tuple,max_length=4)

    @field_validator('workflow_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('author_ref')
    @classmethod
    def author(cls,v):return SubscriptionPreference.canonical_subscriber(v)

    @field_validator('as_of')
    @classmethod
    def aware(cls,v):return Event.aware(v).astimezone(timezone.utc)

    @model_validator(mode='after')
    def integrity(self):
        if self.policy.organization_id!=self.organization_id or any(d.organization_id!=self.organization_id for d in self.decisions):raise ValueError('Cross-tenant workflow')
        if self.as_of!=self.policy.as_of.astimezone(timezone.utc):raise ValueError('Policy evaluation clock mismatch')
        if self.policy_sha256!=simulate_policy(self.policy,self.organization_id)['sha256']:raise ValueError('Stale policy envelope')
        if len({d.role for d in self.decisions})!=len(self.decisions) or len({d.decision_ref for d in self.decisions})!=len(self.decisions):raise ValueError('Duplicate role or decision')
        return self


def simulate_workflow(workflow:ReviewWorkflow,tenant:str):
    if workflow.organization_id!=tenant:raise ValueError('Tenant mismatch')
    policy=simulate_policy(workflow.policy,tenant)
    decisions={d.role:d for d in workflow.decisions}
    actor_counts={d.reviewer_ref:sum(x.reviewer_ref==d.reviewer_ref for x in workflow.decisions) for d in workflow.decisions}
    results=[]
    for role in ROLES:
        flags=[];decision=decisions.get(role)
        if decision is None:flags.append('review-missing')
        else:
            if decision.reviewer_ref==workflow.author_ref:flags.append('self-approval-denied')
            if actor_counts[decision.reviewer_ref]>1:flags.append('reviewer-role-collision')
            if decision.subject_sha256!=workflow.policy_sha256 or decision.subject_revision!=workflow.policy.revision:flags.append('stale-subject-invalidated')
            if decision.decided_at>workflow.as_of:flags.append('decision-in-future')
            if decision.decided_at<workflow.policy.campaign.source_entry.updated_at.astimezone(timezone.utc):flags.append('decision-before-source-revision')
            if decision.outcome!='approve':flags.append('approval-not-recorded')
        results.append({'role':role,'decision_ref':decision.decision_ref if decision else None,'review_valid_for_simulation_only':not flags,'review_flags':flags})
    source_eligible=bool(policy['eligible_variations'])
    complete=source_eligible and all(r['review_valid_for_simulation_only'] for r in results)
    normalized=workflow.model_dump(mode='json',exclude={'policy'});normalized['decisions'].sort(key=lambda d:d['role'])
    return seal({'mode':'offline-editorial-separation-of-duties','fixture':normalized,'reviews':results,
                 'source_policy_eligible_for_preview':source_eligible,'all_reviews_complete_for_simulation':complete,
                 'workflow_state':'review-complete-preview' if complete else 'blocked-preview',
                 'eligible_variations':policy['eligible_variations'] if complete else [],'reviewer_identities_verified':False,
                 'reviewer_roles_verified':False,'live_approval_executed':False,'delivery_authorized':False,'roles_changed':False,
                 'review_integrity_scope':'hash-checked synthetic declarations; no signatures, real identity or role attestation'},tenant,'12.4.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-editorial-separation-of-duties','live_approval_executed':False,'delivery_authorized':False},str(tenant),'12.4.0')


@router.post('/preview')
def preview(payload:ReviewWorkflow,tenant=Depends(_scope)):
    try:return simulate_workflow(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/approve-live')
@router.post('/change-role')
@router.post('/commit')
@router.post('/send')
@router.post('/publish')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live editorial approval operations disabled')
