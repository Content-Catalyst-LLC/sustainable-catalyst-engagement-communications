"""MEDIA-05: tenant-bound, metadata-only WordPress editorial preview bridge.

No persistence, delivery, recipient ingestion, token issuance, or external publishing.
The caller's WordPress approval/fingerprint is an assertion, not independent attestation.
This is a preview-only bridge to the Engagement & Communications review boundary.
"""
import hashlib
import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from .offline_staging import scope


class PrivateBridgeRoute(APIRoute):
    def get_route_handler(self):
        delegate = super().get_route_handler()

        async def sanitized(request):
            try:
                return await delegate(request)
            except RequestValidationError:
                # Never reflect arbitrary source URLs or user-supplied metadata.
                raise HTTPException(422, 'Invalid Media bridge envelope') from None
        return sanitized


router = APIRouter(prefix='/v1/media-bridge', tags=['media05-private-preview'], route_class=PrivateBridgeRoute)
_scope = scope('SCEC_MEDIA05_STAGING_ENABLED')
CHANNELS = ('substack', 'youtube', 'linkedin', 'x', 'facebook', 'instagram', 'threads', 'bluesky', 'mastodon')
# Advisory routing into the existing communications domain vocabulary. Nothing is enqueued.
CHANNEL_WORKFLOW = {c: ('newsletter-alerts' if c == 'substack' else 'campaign-composer') for c in CHANNELS}
BLOCKED_ACTIONS = ('publish', 'send', 'schedule', 'sync', 'commit', 'activate', 'subscribe', 'export-recipients')
HEX_SHA = re.compile(r'^[a-f0-9]{64}$')
PACKAGE_REF = re.compile(r'^wp-media:[1-9][0-9]{0,9}$')


def canonical_site(value: str):
    """Allow only a public HTTPS hostname, never a credential/port/query/IP/localhost."""
    if not isinstance(value, str) or len(value) > 400:
        raise ValueError('Invalid public site URL')
    try:
        p = urlsplit(value)
        host = (p.hostname or '').lower()
        if (p.scheme != 'https' or not host or p.username or p.password or p.port is not None or
                p.query or p.fragment or not p.path.startswith('/') or '..' in host or
                not re.fullmatch(r'[a-z0-9.-]+', host) or '.' not in host or
                host.endswith(('.local', '.localhost', '.internal', '.test', '.invalid')) or host == 'localhost'):
            raise ValueError('Invalid public site URL')
        try:
            ipaddress.ip_address(host)
            raise ValueError('IP destinations forbidden')
        except ValueError as exc:
            if str(exc) == 'IP destinations forbidden':
                raise
        return host
    except (ValueError, AttributeError):
        raise ValueError('Invalid public site URL') from None


class MediaBridgePackage(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    schema_version: Literal['scec.media-bridge/1']
    organization_id: str = Field(min_length=36, max_length=36)
    package_ref: str = Field(min_length=10, max_length=20)
    source_url: str = Field(min_length=12, max_length=400)
    source_content_sha256: str = Field(min_length=64, max_length=64)
    approved_package_sha256: str = Field(min_length=64, max_length=64)
    approved_at_utc: datetime
    channels: tuple[Literal['substack','youtube','linkedin','x','facebook','instagram','threads','bluesky','mastodon'], ...] = Field(min_length=1, max_length=9)
    source_published_attested: StrictBool
    rights_review_attested: StrictBool
    embargo_review_attested: StrictBool
    export_mode: Literal['metadata_preview_only']

    @field_validator('organization_id')
    @classmethod
    def org(cls, value):
        from uuid import UUID
        try:
            u = UUID(value)
            if u.int == 0 or str(u) != value:
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('Invalid organization identifier') from None
        return value

    @field_validator('package_ref')
    @classmethod
    def package(cls, value):
        if not PACKAGE_REF.fullmatch(value):
            raise ValueError('Invalid package reference')
        return value

    @field_validator('source_url')
    @classmethod
    def source(cls, value):
        canonical_site(value)
        return value

    @field_validator('source_content_sha256', 'approved_package_sha256')
    @classmethod
    def digest(cls, value):
        if not HEX_SHA.fullmatch(value):
            raise ValueError('SHA-256 required')
        return value

    @field_validator('approved_at_utc')
    @classmethod
    def timestamp(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Timezone required')
        if value.astimezone(timezone.utc) > datetime.now(timezone.utc):
            raise ValueError('Approval timestamp in future')
        return value

    @field_validator('channels')
    @classmethod
    def channel_set(cls, values):
        if len(values) != len(set(values)):
            raise ValueError('Duplicate channels')
        return tuple(sorted(values))

    @model_validator(mode='after')
    def reviews(self):
        if not (self.source_published_attested and self.rights_review_attested and self.embargo_review_attested):
            raise ValueError('All WordPress review attestations required')
        return self


def assessed_preview(payload: MediaBridgePackage, tenant: str) -> dict:
    if payload.organization_id != tenant:
        raise ValueError('Tenant mismatch')
    host = canonical_site(payload.source_url)
    allowed = {v.strip().lower() for v in os.getenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS', '').split(',') if v.strip()}
    if not allowed or host not in allowed:
        raise ValueError('Source host not allowlisted')
    facts = payload.model_dump(mode='json')
    facts['channels'] = sorted(facts['channels'])
    facts['approved_at_utc'] = payload.approved_at_utc.astimezone(timezone.utc).isoformat()
    digest = hashlib.sha256(json.dumps(facts, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    plan = [{'channel': channel, 'suggested_workflow': CHANNEL_WORKFLOW[channel],
             'handoff': 'manual-only', 'dispatch_enabled': False} for channel in facts['channels']]
    output = {
        'release': 'MEDIA-05', 'schema_version': payload.schema_version,
        'organization_id': tenant, 'package_ref': payload.package_ref,
        'approved_package_sha256': payload.approved_package_sha256,
        'input_sha256': digest, 'source_host': host, 'requested_channels': list(facts['channels']),
        'channel_plan': plan, 'preview_only': True,
        'suggested_workflows_are_not_executed': True,
        'wordpress_approval_independently_verified': False,
        'rights_or_embargo_independently_verified': False,
        'source_fetched': False, 'subscriber_data_ingested': False,
        'delivery_enabled': False, 'auto_post_enabled': False,
        'external_api_called': False, 'persistence_enabled': False,
        'production_certified': False, 'requires_separate_live_acceptance': True,
    }
    output['receipt_sha256'] = hashlib.sha256(json.dumps(output, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    return output


@router.get('/status')
def status(tenant=Depends(_scope)):
    return {
        'release': 'MEDIA-05', 'organization_id': str(tenant),
        'mode': 'private-metadata-preview', 'bridge_enabled': True,
        'publishing_enabled': False, 'sending_enabled': False, 'persistence_enabled': False,
        'external_platforms_connected': False, 'production_certified': False,
    }


@router.post('/preview')
def preview(payload: MediaBridgePackage, tenant=Depends(_scope)):
    try:
        return assessed_preview(payload, str(tenant))
    except ValueError:
        raise HTTPException(422, 'Invalid or unauthorized Media bridge envelope') from None


@router.post('/publish')
@router.post('/send')
@router.post('/schedule')
@router.post('/sync')
@router.post('/commit')
@router.post('/activate')
@router.post('/subscribe')
@router.post('/export-recipients')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503, 'Media bridge outbound actions disabled')
