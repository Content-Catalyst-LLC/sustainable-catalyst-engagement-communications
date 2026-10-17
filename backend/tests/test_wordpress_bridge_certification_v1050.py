import os
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.wordpress_bridge_certification_v1050 import CHANNELS, IntakeBridgeEvidence, preview_evidence, source_report, safety_state

ROOT=Path(__file__).resolve().parents[2]
TENANT=str(uuid4())
@pytest.mark.parametrize('channel,slugs',CHANNELS.items())
def test_all_channel_slug_contracts(channel,slugs):
    for slug in slugs:
        evidence=preview_evidence(IntakeBridgeEvidence(kind=channel,source='synthetic-review',page_slug=slug),TENANT)
        assert evidence['kind']==channel and evidence['persisted'] is False
        assert evidence['forwarded'] is False and evidence['live_page_verified'] is False
        assert len(evidence['evidence_sha256'])==64
@pytest.mark.parametrize('channel,slug',[('contact','feedback'),('feedback','support'),('channel','contact'),('support','channel'),('feature-suggestions','feedback')])
def test_reject_wrong_slug(channel,slug):
    with pytest.raises(ValueError,match='Page does not match'):
        preview_evidence(IntakeBridgeEvidence(kind=channel,source='synthetic-review',page_slug=slug),TENANT)
@pytest.mark.parametrize('invalid',['/contact','../contact','https://example.com','contact?x=1','CONTACT'])
def test_reject_slug_injection(invalid):
    with pytest.raises(Exception):IntakeBridgeEvidence(kind='contact',source='synthetic-review',page_slug=invalid)
def test_consent_never_inferred():
    a=preview_evidence(IntakeBridgeEvidence(kind='contact',source='wordpress-public-launcher',page_slug='contact'),TENANT)
    b=preview_evidence(IntakeBridgeEvidence(kind='contact',source='wordpress-public-launcher',page_slug='contact',consent_to_contact=True),TENANT)
    assert a['consent_recorded_for_preview_only'] is False and b['consent_recorded_for_preview_only'] is True
    assert a['evidence_sha256'] != b['evidence_sha256']
def test_extra_personal_data_rejected():
    with pytest.raises(Exception):IntakeBridgeEvidence(kind='contact',source='synthetic-review',page_slug='contact',email='private@example.test',message='secret')
def test_noncanonical_org_denied():
    obj=IntakeBridgeEvidence(kind='support',source='synthetic-review',page_slug='support')
    with pytest.raises(ValueError):preview_evidence(obj,TENANT.upper())
def test_static_wordpress_contract():
    assert all(source_report(ROOT).values())
def test_default_safe_environment(monkeypatch):
    for key in ('SCEC_HUMAN_AUTH_ENABLED','SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):monkeypatch.delenv(key,raising=False)
    assert all(safety_state().values())
@pytest.mark.parametrize('path', ['/status','/requirements'])
def test_staging_get_disabled(monkeypatch,path):
    monkeypatch.delenv('SCEC_WORDPRESS_BRIDGE_CERT_STAGING_ENABLED',raising=False)
    assert TestClient(app).get('/v1/wordpress-intake-certification'+path).status_code in (401,503)
@pytest.mark.parametrize('path', ['/preview','/commit','/certify','/promote','/forward'])
def test_staging_post_disabled(monkeypatch,path):
    monkeypatch.delenv('SCEC_WORDPRESS_BRIDGE_CERT_STAGING_ENABLED',raising=False)
    response=TestClient(app).post('/v1/wordpress-intake-certification'+path,json={})
    assert response.status_code in (401,422,503)
def test_no_mutation_in_certification_module():
    content=(ROOT/'backend/app/wordpress_bridge_certification_v1050.py').read_text()
    assert not any(token in content for token in ('requests.post(', 'urllib.request.urlopen(', 'sqlite3.connect(', 'psycopg.connect('))
