from datetime import date
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.privacy_consent_retention_v1060 import PrivacyPreview, classify, RETENTION, PURPOSE, safety_state
TENANT=str(uuid4())

def payload(channel='contact', **kw):
    from app.wordpress_bridge_certification_v1050 import CHANNELS
    params=dict(channel=channel,page_slug=CHANNELS[channel][0],simulated_received_date=date(2026,1,1),simulated_as_of=date(2026,2,1))
    params.update(kw)
    return PrivacyPreview(**params)

@pytest.mark.parametrize('channel',list(RETENTION))
def test_five_channel_draft_retention(channel):
    result=classify(payload(channel),TENANT)
    assert result['retention_days_draft']==RETENTION[channel]
    assert result['purpose']==PURPOSE[channel]
    assert result['personal_data_collected'] is False
    assert result['persisted'] is False and result['deleted'] is False
    assert result['outbound_sent'] is False and result['federated'] is False
    assert result['production_policy_approved'] is False
    assert len(result['evidence_sha256'])==64

@pytest.mark.parametrize('channel',list(RETENTION))
def test_due_date_boundary(channel):
    from datetime import timedelta
    d=date(2026,1,1)+timedelta(days=RETENTION[channel])
    assert not classify(payload(channel,simulated_as_of=d-timedelta(days=1)),TENANT)['retention_review_due']
    assert classify(payload(channel,simulated_as_of=d),TENANT)['retention_review_due']

def test_noncanonical_tenant_denied():
    with pytest.raises(ValueError):classify(payload(),TENANT.upper())

def test_wrong_page_denied():
    with pytest.raises(ValueError,match='mismatch'):classify(payload(page_slug='support'),TENANT)

def test_future_received_denied():
    with pytest.raises(ValueError):classify(payload(simulated_received_date=date(2026,3,1)),TENANT)

def test_consent_lawful_basis():
    with pytest.raises(ValueError):classify(payload(lawful_basis='consent'),TENANT)
    with pytest.raises(ValueError):classify(payload(consent_explicit=True),TENANT)
    assert classify(payload(lawful_basis='consent',consent_explicit=True),TENANT)['consent_explicit_for_preview']

def test_personal_data_rejected():
    with pytest.raises(Exception):PrivacyPreview(**payload().model_dump(),email='person@example.test',message='sensitive')

def test_synthetic_reference_never_echoed():
    output=classify(payload(synthetic_reference='fake_ref_01'),TENANT)
    assert 'fake_ref_01' not in repr(output)

def test_fail_closed_environment(monkeypatch):
    for key in ('SCEC_HUMAN_AUTH_ENABLED','SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):monkeypatch.delenv(key,raising=False)
    assert safety_state()
    monkeypatch.setenv('SCEC_DELETION_ENABLED','1')
    assert not safety_state()

@pytest.mark.parametrize('path', ['/status','/policy-draft'])
def test_default_disabled_get(monkeypatch,path):
    monkeypatch.delenv('SCEC_PRIVACY_RETENTION_STAGING_ENABLED',raising=False)
    assert TestClient(app).get('/v1/privacy-consent-retention'+path).status_code in (401,503)

@pytest.mark.parametrize('path', ['/preview','/approve','/delete','/commit','/export','/promote'])
def test_default_disabled_post(monkeypatch,path):
    monkeypatch.delenv('SCEC_PRIVACY_RETENTION_STAGING_ENABLED',raising=False)
    assert TestClient(app).post('/v1/privacy-consent-retention'+path,json={}).status_code in (401,422,503)

def test_no_transport_or_database_in_module():
    source=(Path(__file__).resolve().parents[1]/'app/privacy_consent_retention_v1060.py').read_text()
    assert not any(x in source for x in ('urllib.request.urlopen(', 'requests.post(', 'psycopg.connect(', 'sqlite3.connect(', 'os.remove(', 'unlink('))
