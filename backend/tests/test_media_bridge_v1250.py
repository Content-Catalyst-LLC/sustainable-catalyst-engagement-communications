"""MEDIA-05 offline backend security/contract acceptance. No outbound traffic."""
import copy
import hashlib
import json
import time
from datetime import datetime, timezone
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.media_bridge_v1250 import (
    MediaBridgePackage, assessed_preview, canonical_site, BLOCKED_ACTIONS,
)
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

ORG='00000000-0000-4000-8000-000000000001'
OTHER='00000000-0000-4000-8000-000000000002'
KEY='synthetic-testing-not-a-production-signing-key-01234567'


def envelope(**changes):
    raw={
        'schema_version':'scec.media-bridge/1',
        'organization_id':ORG,
        'package_ref':'wp-media:101',
        'source_url':'https://sustainablecatalyst.com/verified-public-paper/',
        'source_content_sha256':'a'*64,
        'approved_package_sha256':'b'*64,
        'approved_at_utc':'2026-11-08T00:00:00+00:00',
        'channels':['substack','linkedin'],
        'source_published_attested':True,
        'rights_review_attested':True,
        'embargo_review_attested':True,
        'export_mode':'metadata_preview_only',
    }
    return {**raw,**changes}


@pytest.fixture
def configured(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):
        monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    monkeypatch.setenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS','sustainablecatalyst.com')
    monkeypatch.setenv('SCEC_MEDIA05_STAGING_ENABLED','1')
    return TestClient(app)


def headers(org=ORG, roles=('administrator',), sign_org=None):
    return {
        'Authorization':'Bearer '+mint_token(subject='synthetic-media-bridge-review',
            organization_id=sign_org or org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),
        'X-SCEC-Organization-ID':org,
    }


def test_url_allowlist_rejects_internal_or_hostile_domains():
    for url in ('http://sustainablecatalyst.com/foo/','https://localhost/foo/',
                'https://127.0.0.1/foo/','https://sustainablecatalyst.local/foo/',
                'https://u:pw@sustainablecatalyst.com/foo/','https://sustainablecatalyst.com:443/foo/',
                'https://sustainablecatalyst.com/foo/?token=abc','https://sustainablecatalyst.com/foo/#id'):
        with pytest.raises(ValueError):canonical_site(url)
    assert canonical_site('https://sustainablecatalyst.com/public/wasp/')=='sustainablecatalyst.com'


def test_schema_strictly_rejects_private_material_and_invalid_review():
    for fields in [
        {'subscriber_email':'name@example.org'}, {'access_token':'secret'},
        {'channels':['linkedin','linkedin']}, {'channels':['unknown']},
        {'rights_review_attested':False}, {'embargo_review_attested':False},
        {'source_published_attested':False}, {'rights_review_attested':'true'},
        {'approved_package_sha256':'UPPERCASE'}, {'package_ref':'wp-media:0'},
        {'approved_at_utc':'2026-11-08T00:00:00'}, {'export_mode':'automatic'},
        {'organization_id':'ABCDEF01-0000-4000-8000-000000000001'},
    ]:
        with pytest.raises(ValidationError):MediaBridgePackage(**envelope(**fields))


def test_preview_is_attestation_not_publication(monkeypatch):
    monkeypatch.setenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS','sustainablecatalyst.com')
    preview=assessed_preview(MediaBridgePackage(**envelope()), ORG)
    assert preview['preview_only'] is True
    for name in ['delivery_enabled','auto_post_enabled','persistence_enabled',
                 'source_fetched','external_api_called','subscriber_data_ingested',
                 'production_certified','wordpress_approval_independently_verified',
                 'rights_or_embargo_independently_verified']:
        assert preview[name] is False
    assert preview['channel_plan']==[
        {'channel':'linkedin','suggested_workflow':'campaign-composer','handoff':'manual-only','dispatch_enabled':False},
        {'channel':'substack','suggested_workflow':'newsletter-alerts','handoff':'manual-only','dispatch_enabled':False},
    ]
    assert len(preview['input_sha256'])==64 and len(preview['receipt_sha256'])==64
    assert preview['approved_package_sha256']=='b'*64
    assert 'source_url' not in preview and 'bearer' not in str(preview).lower()
    assert assessed_preview(MediaBridgePackage(**envelope(channels=['linkedin','substack'])), ORG)['input_sha256']==preview['input_sha256']


def test_tenant_and_site_authority_rejected(monkeypatch):
    monkeypatch.setenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS','sustainablecatalyst.com')
    p=MediaBridgePackage(**envelope())
    with pytest.raises(ValueError):assessed_preview(p,OTHER)
    monkeypatch.setenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS','another.example')
    with pytest.raises(ValueError):assessed_preview(p,ORG)
    monkeypatch.delenv('SCEC_MEDIA05_ALLOWED_SITE_HOSTS')
    with pytest.raises(ValueError):assessed_preview(p,ORG)


def test_flag_disabled_by_default(configured,monkeypatch):
    monkeypatch.setenv('SCEC_MEDIA05_STAGING_ENABLED','0')
    r=configured.get('/v1/media-bridge/status',headers=headers())
    assert r.status_code==503
    assert configured.post('/v1/media-bridge/preview',json=envelope(),headers=headers()).status_code==503


def test_authenticated_admin_only_and_tenant_scoped(configured):
    assert configured.get('/v1/media-bridge/status').status_code==401
    assert configured.get('/v1/media-bridge/status',headers=headers(roles=('viewer',))).status_code==403
    assert configured.get('/v1/media-bridge/status',headers=headers(org=OTHER)).status_code==403
    assert configured.get('/v1/media-bridge/status',headers=headers(org=ORG,sign_org=OTHER)).status_code==403
    r=configured.get('/v1/media-bridge/status',headers=headers())
    assert r.status_code==200
    assert r.json()['production_certified'] is False
    assert r.json()['external_platforms_connected'] is False


def test_private_preview_accepts_only_mapped_metadata(configured):
    r=configured.post('/v1/media-bridge/preview',json=envelope(),headers=headers())
    assert r.status_code==200,r.text
    assert r.json()['package_ref']=='wp-media:101'
    assert r.json()['requested_channels']==['linkedin','substack']
    assert r.json()['delivery_enabled'] is False
    assert r.json()['persistence_enabled'] is False
    for modified in [envelope(source_url='https://other.example/post/'),
                     envelope(organization_id=OTHER),
                     envelope(channels=['linkedin','linkedin']),
                     envelope(rights_review_attested=False),
                     envelope(source_url='https://127.0.0.1/private/')]:
        response=configured.post('/v1/media-bridge/preview',json=modified,headers=headers())
        assert response.status_code==422
        assert 'other.example' not in response.text and '127.0.0.1' not in response.text


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_delivery_and_mutations_never_enabled(configured, action):
    response=configured.post('/v1/media-bridge/'+action,json=envelope(),headers=headers())
    assert response.status_code==503


def test_danger_flag_blocks_bridge(configured,monkeypatch):
    monkeypatch.setenv('SCEC_PRODUCTION_WRITES_ENABLED','1')
    assert configured.get('/v1/media-bridge/status',headers=headers()).status_code==503
    assert configured.post('/v1/media-bridge/preview',json=envelope(),headers=headers()).status_code==503


def test_legacy_mode_cannot_enter_bridge(configured,monkeypatch):
    monkeypatch.setenv('SCEC_IDENTITY_MODE','legacy')
    assert configured.get('/v1/media-bridge/status').status_code==503
