import pytest
from uuid import uuid4
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.production_acceptance_v1090 import GATES,RELEASES,PROTECTED,BLOCKED_ACTIONS,EvidencePreview,acceptance_report,preview,safety_state
TENANT=str(uuid4())
def sample(**kw):
    data=dict(reference='synthetic-review',evidence_key='synthetic-evidence-01',claimed_gate=GATES[0],evidence_kind='synthetic-test')
    data.update(kw)
    return EvidencePreview(**data)
def test_release_and_lineage():
    assert RELEASES==tuple(f'10.{i}.0' for i in range(10))
    assert app.version=='12.5.0'
    assert set(PROTECTED)=={'contact','feedback','feature-suggestions','channel','support'}
def test_all_seven_pending():
    report=acceptance_report(source_preflight_passed=True)
    assert report['source_preflight_passed'] and len(report['gate_states'])==7
    assert set(report['gate_states'].values())=={'pending-live-evidence'}
    assert not report['live_checks'] and not report['production_certified']
@pytest.mark.parametrize('field',('production_certified','production_writes_enabled','outbound_communications_enabled','human_login_enabled','deletion_enabled','federation_enabled','automatic_promotion_enabled','production_approval_granted'))
def test_never_activate(field):
    assert acceptance_report()[field] is False
@pytest.mark.parametrize('gate',GATES)
def test_synthetic_evidence_never_certifies_gate(gate):
    report=preview(sample(claimed_gate=gate,review_acknowledged=True),TENANT)
    assert not report['gate_certified'] and not report['evidence_verified_against_live_system']
    assert not report['evidence_persisted'] and not report['production_certified']
    assert report['gate_states'][gate]=='pending-live-evidence'
def test_fingerprint_tenant_bound_and_deterministic():
    a=preview(sample(),TENANT);b=preview(sample(),TENANT);c=preview(sample(evidence_key='different-123456'),TENANT)
    assert a['synthetic_evidence_sha256']==b['synthetic_evidence_sha256']!=c['synthetic_evidence_sha256']
    assert 'synthetic-evidence-01' not in repr(a)
def test_noncanonical_tenant_rejected():
    with pytest.raises(ValueError):preview(sample(),TENANT.upper())
@pytest.mark.parametrize('field,value', [('evidence_key','short'),('reference','ab'),('evidence_kind','live-certified'),('claimed_gate','false-gate')])
def test_evidence_contract_rejects_invalid(field,value):
    with pytest.raises(ValidationError):EvidencePreview(**{**sample().model_dump(),field:value})
@pytest.mark.parametrize('field',('email','message_body','token','customer_data','logs'))
def test_no_pii_fields(field):
    with pytest.raises(ValidationError):EvidencePreview(**{**sample().model_dump(),field:'secret'})
def test_safety_state_fail_closed(monkeypatch):
    from app.wordpress_bridge_certification_v1050 import DANGER_FLAGS
    for flag in DANGER_FLAGS:monkeypatch.setenv(flag,'0')
    assert safety_state()
    for flag in DANGER_FLAGS:
        monkeypatch.setenv(flag,'1');assert not safety_state();monkeypatch.setenv(flag,'0')
@pytest.mark.parametrize('path',('/status','/gates'))
def test_default_gated_reads(monkeypatch,path):
    monkeypatch.setenv('SCEC_ACCEPTANCE_STAGING_ENABLED','0')
    assert TestClient(app).get('/v1/production-acceptance'+path).status_code in (401,503)
@pytest.mark.parametrize('path',('/evidence-preview',)+tuple('/'+s for s in BLOCKED_ACTIONS))
def test_default_gated_posts(monkeypatch,path):
    monkeypatch.setenv('SCEC_ACCEPTANCE_STAGING_ENABLED','0')
    assert TestClient(app).post('/v1/production-acceptance'+path,json={}).status_code in (401,422,503)
def test_source_no_side_effects():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'app/production_acceptance_v1090.py').read_text()
    assert not any(x in source for x in ('httpx.post(', 'requests.post(', 'subprocess.run(', 'sqlite3.connect(', 'psycopg.connect(', 'smtplib.SMTP(', 'wp_remote_post(', 'os.remove('))
