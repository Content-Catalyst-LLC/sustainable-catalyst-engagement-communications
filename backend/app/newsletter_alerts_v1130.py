"""Offline synthetic newsletter/alert previews. No subscribers, persistence or transport."""
import hashlib
import json
import os
import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from .identity import Principal, bound_mode, principal, tenant_for_principal
from .production_acceptance_v1090 import GATES as LIVE_GATES
from .wordpress_bridge_certification_v1050 import DANGER_FLAGS

class SyntheticPreviewRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        async def sanitized(request):
            try:
                return await original(request)
            except RequestValidationError:
                # Never reflect submitted contact values or malformed tenant data.
                raise HTTPException(422, 'Invalid synthetic alert contract') from None
        return sanitized


router = APIRouter(prefix='/v1/research-alerts', tags=['newsletter-research-alerts-staging'], route_class=SyntheticPreviewRoute)
Topic = Literal['climate-nature','energy-systems','sustainable-development','methods-data',
                'economics-policy','law-governance','health-society','technology-innovation']
Frequency = Literal['immediate','daily','weekly','monthly']
Channel = Literal['email','in-app']
TOPICS = {
    'climate-nature': 'Climate, ecosystems and biodiversity',
    'energy-systems': 'Energy technologies and transitions',
    'sustainable-development': 'Sustainable development and resilience',
    'methods-data': 'Research methods, datasets and reproducibility',
    'economics-policy': 'Economics, institutions and public policy',
    'law-governance': 'Law, governance and public accountability',
    'health-society': 'Health, communities and social systems',
    'technology-innovation': 'Technology, computation and innovation',
}
FREQUENCIES = ('immediate','daily','weekly','monthly')
CHANNELS = ('email','in-app')
STATES = ('draft','review','approved-preview','denied')
REVIEW_GATES = ('consent','privacy','editorial','source-integrity','distribution','rights','production-acceptance')
BLOCKED_ACTIONS = ('subscribe','activate','send','publish','syndicate','schedule','enqueue','delete','federate','token-exchange','export-contacts')
EXTRA_DANGER_FLAGS = ('SCEC_PRODUCTION_WRITES_ENABLED','SCEC_PUBLICATION_ENABLED',
                      'SCEC_SYNDICATION_ENABLED','SCEC_SCHEDULED_DELIVERY_ENABLED','SCEC_TOKEN_EXCHANGE_ENABLED')


def organization(value: str) -> str:
    if str(UUID(value)) != value or UUID(value).int == 0:
        raise ValueError('Canonical nonzero organization UUID required')
    return value


def opaque(value: str) -> str:
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{2,95}', value):
        raise ValueError('Opaque research reference required')
    return value


def plain(value: str) -> str:
    # This is a bounded fixture contract, not a general-purpose PII detector.
    if re.search(r'[<>@]|https?://|\+?\d[\d\s().-]{7,}\d', value, re.I):
        raise ValueError('Use plain synthetic text without contacts, URLs or markup')
    return value


class Fixture(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    synthetic: Literal[True]
    organization_id: str = Field(min_length=36, max_length=36)

    @field_validator('synthetic', mode='before')
    @classmethod
    def synthetic_only(cls, value):
        if type(value) is not bool or value is not True:
            raise ValueError('Explicit synthetic fixture required')
        return value

    @field_validator('organization_id')
    @classmethod
    def canonical_organization(cls, value):
        return organization(value)


class SubscriptionPreference(Fixture):
    subscriber_ref: str = Field(pattern=r'^synthetic:[0-9a-f-]{36}$', max_length=46)
    topics: list[Topic] = Field(min_length=1, max_length=8)
    frequency: Frequency = 'weekly'
    channels: list[Channel] = Field(min_length=1, max_length=2)
    consent: StrictBool = False
    state: Literal['active-preview','opted-out','suppressed'] = 'opted-out'

    @field_validator('subscriber_ref')
    @classmethod
    def canonical_subscriber(cls, value):
        if 'synthetic:' + str(UUID(value[10:])) != value or UUID(value[10:]).int == 0:
            raise ValueError('Synthetic nonzero opaque UUID required')
        return value

    @field_validator('topics','channels')
    @classmethod
    def unique(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Repeated preference values')
        return values


class ResearchAlert(Fixture):
    object_ref: str = Field(min_length=3, max_length=96)
    revision: str = Field(min_length=1, max_length=48, pattern=r'^[A-Za-z0-9_.:-]+$')
    headline: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1, max_length=600)
    source_refs: list[str] = Field(min_length=1, max_length=12)
    topics: list[Topic] = Field(min_length=1, max_length=8)
    review_state: Literal['draft','review','approved-preview','denied'] = 'draft'
    privacy_reviewed: StrictBool = False
    editorial_reviewed: StrictBool = False
    source_integrity_reviewed: StrictBool = False
    distribution_reviewed: StrictBool = False
    rights_reviewed: StrictBool = False

    @field_validator('object_ref')
    @classmethod
    def reference(cls, value):
        return opaque(value)

    @field_validator('headline','summary')
    @classmethod
    def text(cls, value):
        return plain(value)

    @field_validator('source_refs')
    @classmethod
    def sources(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Repeated source references')
        return [opaque(v) for v in values]

    @field_validator('topics')
    @classmethod
    def unique_topics(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Repeated topics')
        return values


class AlertPreview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    alert: ResearchAlert
    preferences: list[SubscriptionPreference] = Field(min_length=1, max_length=100)
    frequency: Frequency = 'weekly'
    channel: Channel = 'email'

    @model_validator(mode='after')
    def unique_tenant_fixture(self):
        refs = [p.subscriber_ref for p in self.preferences]
        if len(refs) != len(set(refs)):
            raise ValueError('Repeated synthetic subscriber reference')
        if any(p.organization_id != self.alert.organization_id for p in self.preferences):
            raise ValueError('Fixture crosses organization boundaries')
        return self


def compose(payload: AlertPreview, organization_id: str) -> dict:
    tenant = organization(organization_id)
    if tenant != payload.alert.organization_id:
        raise ValueError('Fixture crosses organization boundaries')
    alert = payload.alert
    checks = {'privacy': alert.privacy_reviewed, 'editorial': alert.editorial_reviewed,
              'source-integrity': alert.source_integrity_reviewed,
              'distribution': alert.distribution_reviewed, 'rights': alert.rights_reviewed}
    reviewed = all(checks.values()) and alert.review_state == 'approved-preview'
    matches, excluded = [], []
    preferences = []
    for pref in sorted(payload.preferences, key=lambda p: p.subscriber_ref):
        reasons = []
        if not pref.consent: reasons.append('missing-consent')
        if pref.state != 'active-preview': reasons.append(pref.state)
        if not set(pref.topics).intersection(alert.topics): reasons.append('topic-mismatch')
        if pref.frequency != payload.frequency: reasons.append('frequency-mismatch')
        if payload.channel not in pref.channels: reasons.append('channel-mismatch')
        if not reviewed: reasons.append('review-incomplete-or-denied')
        if reasons: excluded.append({'synthetic_ref': pref.subscriber_ref, 'reasons': reasons})
        else: matches.append(pref.subscriber_ref)
        normalized = pref.model_dump(); normalized['topics'] = sorted(pref.topics); normalized['channels'] = sorted(pref.channels)
        preferences.append(normalized)
    normalized_alert = alert.model_dump()
    normalized_alert['topics'] = sorted(alert.topics)
    normalized_alert['source_refs'] = sorted(alert.source_refs)
    document = {'organization_id': tenant, 'alert': normalized_alert,
                'synthetic_preferences': preferences, 'frequency_preview': payload.frequency,
                'channel_preview': payload.channel, 'matched_synthetic_refs': matches,
                'excluded_synthetic_refs': excluded,
                'review_gates': {**checks, 'consent': all(p.consent for p in payload.preferences), 'production-acceptance': False}}
    fingerprint = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode()).hexdigest()
    return {'release': '11.3.0', 'mode': 'offline-synthetic-alert-preview', **document,
            'sha256': fingerprint, 'preview_eligible_count': len(matches),
            'review_complete_for_preview_only': reviewed,
            **{k: False for k in ('publication_authorized','actual_publication_enabled','actual_syndication_enabled',
                                  'subscription_activation_enabled','outbound_communications_enabled','scheduled_delivery_enabled',
                                  'persisted','source_fetch_performed','human_login_enabled','deletion_enabled',
                                  'federation_enabled','token_exchange_enabled','production_writes_enabled','production_certified')},
            'live_acceptance_gates_pending': list(LIVE_GATES)}


def _scope(x_scec_organization_id: str | None = Header(default=None), actor: Principal | None = Depends(principal)):
    if os.getenv('SCEC_ALERTS_STAGING_ENABLED','0') != '1' or any(os.getenv(k,'0') != '0' for k in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS)):
        raise HTTPException(503, 'Research alert staging disabled')
    if not bound_mode(): raise HTTPException(503, 'Bound service identity required')
    tenant = tenant_for_principal(x_scec_organization_id, actor)
    if str(tenant) not in {v.strip() for v in os.getenv('SCEC_ALLOWED_ORGANIZATION_IDS','').split(',') if v.strip()}:
        raise HTTPException(403, 'Tenant not allowlisted')
    if not actor.roles.intersection({'administrator'}): raise HTTPException(403, 'Privileged role required')
    return tenant


@router.get('/status')
def status(tenant=Depends(_scope)):
    return {'release':'11.3.0','organization_id':str(tenant),'mode':'offline-synthetic-alert-preview',
            'topics':TOPICS,'frequencies':FREQUENCIES,'channel_preview_types':CHANNELS,
            'production_certified':False,'production_writes_enabled':False,
            'live_acceptance_gates_pending':list(LIVE_GATES)}


@router.post('/preview')
def preview(payload: AlertPreview, tenant=Depends(_scope)):
    try: return compose(payload,str(tenant))
    except ValueError: raise HTTPException(422,'Fixture organization mismatch') from None


@router.post('/subscribe')
@router.post('/activate')
@router.post('/send')
@router.post('/publish')
@router.post('/syndicate')
@router.post('/schedule')
@router.post('/enqueue')
@router.post('/delete')
@router.post('/federate')
@router.post('/token-exchange')
@router.post('/export-contacts')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live alert and subscription operations disabled')
