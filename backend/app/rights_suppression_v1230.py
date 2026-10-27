"""Synthetic purpose, rights, retention and suppression simulation; no consent mutation."""
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, field_validator, model_validator
from .communication_objects_v1200 import FrozenFixture
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque
from .campaigns_v1220 import Campaign, Channel, compose_campaign
from .privacy_governance_v970 import GovernanceItem, inspect as inspect_governance
from .events_v1160 import Event
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/communications-policy',tags=['communications-policy-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_POLICY_STAGING_ENABLED')
BLOCKED_ACTIONS=('grant-consent','subscribe','delete-records','send','publish','activate','federate','export-identities')
PURPOSE_CHANNELS={'research-alert':{'digest','research-alert'},'institutional-update':{'newsroom','digest'},'press-information':{'press-brief'}}


class PurposeRule(FrozenFixture):
    purpose: Literal['research-alert','institutional-update','press-information']
    consent_state: Literal['not-recorded','granted','denied','withdrawn']='not-recorded'
    consent_reviewed: StrictBool=False
    evidence_ref: str | None = Field(default=None,min_length=3,max_length=96)
    allowed_channels: tuple[Channel,...] = Field(default_factory=tuple,max_length=4)
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @field_validator('evidence_ref')
    @classmethod
    def reference(cls,v):return opaque(v) if v is not None else None

    @field_validator('allowed_channels')
    @classmethod
    def channels(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Duplicate channel')
        return tuple(sorted(v))

    @field_validator('valid_from','valid_until')
    @classmethod
    def aware(cls,v):return Event.aware(v) if v is not None else None

    @model_validator(mode='after')
    def validity(self):
        if self.valid_from and self.valid_until and self.valid_until.astimezone(timezone.utc)<=self.valid_from.astimezone(timezone.utc):raise ValueError('Positive validity window required')
        return self


class RightsRule(FrozenFixture):
    source_ref: str = Field(min_length=3,max_length=96)
    policy_revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    license: Literal['unknown','public-domain','cc-by','cc-by-sa','author-owned','permission-required','restricted']='unknown'
    rights_reviewed: StrictBool=False
    attribution_reviewed: StrictBool=False
    permission_documented: StrictBool=False

    @field_validator('source_ref')
    @classmethod
    def reference(cls,v):return opaque(v)


class RetentionRule(FrozenFixture):
    recorded_day: date | None = None
    retention_days: int | None = Field(default=None,strict=True,ge=1,le=36500)
    privacy_reviewed: StrictBool=False
    deletion_hold: StrictBool=False


class PolicySimulation(Fixture):
    policy_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    campaign: Campaign
    campaign_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    as_of: datetime
    purpose_rule: PurposeRule
    rights: tuple[RightsRule,...] = Field(default_factory=tuple,max_length=20)
    retention: RetentionRule
    classification: Literal['public','internal','restricted']='restricted'
    embargo_until: datetime | None = None
    embargo_reviewed: StrictBool=False
    suppressed: StrictBool=False

    @field_validator('policy_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('as_of','embargo_until')
    @classmethod
    def aware(cls,v):return Event.aware(v) if v is not None else None

    @model_validator(mode='after')
    def integrity(self):
        if any(x.organization_id!=self.organization_id for x in [self.campaign,self.purpose_rule,self.retention,*self.rights]):raise ValueError('Cross-tenant policy')
        if self.campaign_sha256!=compose_campaign(self.campaign,self.organization_id)['sha256']:raise ValueError('Stale campaign digest')
        if len({r.source_ref for r in self.rights})!=len(self.rights):raise ValueError('Duplicate rights metadata')
        if any(r.source_ref not in self.campaign.source_entry.source_refs for r in self.rights):raise ValueError('Unregistered rights source')
        return self


def simulate_policy(policy:PolicySimulation,tenant:str):
    if policy.organization_id!=tenant:raise ValueError('Tenant mismatch')
    campaign=compose_campaign(policy.campaign,tenant);p=policy.purpose_rule;r=policy.retention
    # Reuse the existing metadata-only governance checks; these declared
    # synthetic states are never verified legal consent or deletion authority.
    governance=inspect_governance(GovernanceItem(channel='communications',purpose='communications',legal_basis='consent',consent_state=p.consent_state,collected_day=r.recorded_day,retention_days=r.retention_days,deletion_hold=r.deletion_hold),policy.as_of.astimezone(timezone.utc).date())
    reasons=[]
    if not campaign['eligible_for_bundle_only']:reasons.append('source-bundle-ineligible')
    if p.consent_state!='granted':reasons.append('synthetic-consent-not-granted')
    if not p.consent_reviewed or not p.evidence_ref:reasons.append('consent-evidence-review-required')
    if not p.valid_from or not p.valid_until:reasons.append('consent-validity-missing')
    elif not (p.valid_from.astimezone(timezone.utc)<=policy.as_of.astimezone(timezone.utc)<p.valid_until.astimezone(timezone.utc)):reasons.append('consent-outside-validity')
    if not r.privacy_reviewed:reasons.append('privacy-retention-review-required')
    reasons.extend(governance['issues'])
    if policy.classification!='public':reasons.append('nonpublic-content-denied')
    if not policy.embargo_reviewed:reasons.append('embargo-review-required')
    if policy.embargo_until and policy.as_of.astimezone(timezone.utc)<policy.embargo_until.astimezone(timezone.utc):reasons.append('embargo-active')
    if policy.suppressed:reasons.append('suppressed')
    rights={item.source_ref:item for item in policy.rights}
    for source in policy.campaign.source_entry.source_refs:
        if source not in rights:reasons.append('source-rights-missing');continue
        item=rights[source]
        if item.license in ('unknown','restricted'):reasons.append('license-not-permitted')
        if not item.rights_reviewed or not item.attribution_reviewed:reasons.append('source-rights-review-required')
        if item.license in ('author-owned','permission-required') and not item.permission_documented:reasons.append('source-permission-required')
    decisions=[]
    for channel in sorted(policy.campaign.channels):
        flags=set(reasons)
        if channel not in p.allowed_channels:flags.add('channel-consent-not-declared')
        if channel not in PURPOSE_CHANNELS[p.purpose]:flags.add('purpose-channel-mismatch')
        decisions.append({'channel':channel,'eligible_for_synthetic_policy_preview_only':not flags,'review_flags':sorted(flags)})
    eligible={d['channel'] for d in decisions if d['eligible_for_synthetic_policy_preview_only']}
    # The campaign hash covers all source metadata; policy fixture binds only
    # its digest plus the complete normalized policy facts, not raw recipients.
    normalized=policy.model_dump(mode='json',exclude={'campaign'});normalized['rights'].sort(key=lambda x:x['source_ref'])
    for field in ('as_of','embargo_until'):
        value=getattr(policy,field)
        if value:normalized[field]=value.astimezone(timezone.utc).isoformat()
    for field in ('valid_from','valid_until'):
        value=getattr(p,field)
        if value:normalized['purpose_rule'][field]=value.astimezone(timezone.utc).isoformat()
    return seal({'mode':'offline-consent-rights-suppression-simulation','fixture':normalized,'channel_decisions':decisions,
                 'eligible_variations':[v for v in campaign['variations'] if v['channel'] in eligible],
                 'governance_preview':governance,'consent_verified':False,'consent_changed':False,'erasure_authorized':False,
                 'actual_records_deleted':False,'policy_authorizes_delivery':False,'legal_determination':False},tenant,'12.3.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-consent-rights-suppression-simulation','consent_verified':False,'policy_authorizes_delivery':False},str(tenant),'12.3.0')


@router.post('/preview')
def preview(payload:PolicySimulation,tenant=Depends(_scope)):
    try:return simulate_policy(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/grant-consent')
@router.post('/subscribe')
@router.post('/delete-records')
@router.post('/send')
@router.post('/publish')
@router.post('/activate')
@router.post('/federate')
@router.post('/export-identities')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live policy and delivery operations disabled')
