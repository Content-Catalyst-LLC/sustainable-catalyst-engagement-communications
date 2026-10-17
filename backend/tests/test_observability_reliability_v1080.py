from pathlib import Path
from uuid import uuid4
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.observability_reliability_v1080 import ReliabilityScenario,assess,safety_state,FAILURES,RETRY_SECONDS
TENANT=str(uuid4())
def scenario(**kw):
    data=dict(reference='synthetic-incident',incident_key='synthetic-key-001',component='backend',failure='timeout')
    data.update(kw)
    return ReliabilityScenario(**data)
@pytest.mark.parametrize('failure',FAILURES)
def test_no_side_effects(failure):
    x=assess(scenario(failure=failure),TENANT)
    assert not x['live_metrics_collected'] and not x['alerts_sent'] and not x['recovery_executed']
    assert not x['production_certified'] and not x['persisted'] and x['retries_executed']==0
@pytest.mark.parametrize('failure',('authorization-denied','integrity-failure'))
def test_critical_escalation_no_auto_recovery(failure):
    x=assess(scenario(failure=failure),TENANT)
    assert x['severity']=='critical' and x['suggested_action_preview']=='human-incident-escalation'
    assert x['retry_delay_seconds_preview'] is None
@pytest.mark.parametrize('attempt,delay',[(0,60),(1,300),(2,1800),(3,None),(4,None),(5,None)])
def test_backoff_only_simulated(attempt,delay):
    assert assess(scenario(attempt=attempt),TENANT)['retry_delay_seconds_preview']==delay
@pytest.mark.parametrize('failure',('none','invalid-contract'))
def test_non_retryable(failure):
    assert assess(scenario(failure=failure),TENANT)['retry_delay_seconds_preview'] is None
def test_tenant_deterministic_evidence():
    a=assess(scenario(),TENANT); b=assess(scenario(),TENANT); c=assess(scenario(attempt=1),TENANT)
    assert a['synthetic_evidence_sha256']==b['synthetic_evidence_sha256']!=c['synthetic_evidence_sha256']
    assert len(a['synthetic_evidence_sha256'])==64 and 'synthetic-key-001' not in repr(a)
def test_reject_noncanonical_tenant():
    with pytest.raises(ValueError):assess(scenario(),TENANT.upper())
@pytest.mark.parametrize('field,value', [('attempt',6),('synthetic_observed_seconds',3601),('synthetic_affected_count',10001),('failure','made-up'),('reference','a')])
def test_bounds(field,value):
    with pytest.raises(ValidationError):ReliabilityScenario(**{**scenario().model_dump(),field:value})
@pytest.mark.parametrize('field',('email','logs','message_body','customer_data'))
def test_reject_pii_and_logs(field):
    with pytest.raises(ValidationError):ReliabilityScenario(**{**scenario().model_dump(),field:'sensitive'})
def test_danger_flags_fail_closed(monkeypatch):
    for flag in ('SCEC_HUMAN_AUTH_ENABLED','SCEC_PERSISTENCE_ENABLED','SCEC_OUTBOUND_ENABLED','SCEC_DELETION_ENABLED','SCEC_FEDERATION_ENABLED'):monkeypatch.setenv(flag,'0')
    assert safety_state()
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    assert not safety_state()
@pytest.mark.parametrize('endpoint',('/status','/contracts'))
def test_gated_reads(monkeypatch,endpoint):
    monkeypatch.setenv('SCEC_RELIABILITY_STAGING_ENABLED','0')
    assert TestClient(app).get('/v1/observability-reliability'+endpoint).status_code in (401,503)
@pytest.mark.parametrize('endpoint',('/assess','/collect','/alert','/retry','/recover','/restore','/create-incident','/promote'))
def test_blocked_post(monkeypatch,endpoint):
    monkeypatch.setenv('SCEC_RELIABILITY_STAGING_ENABLED','0')
    assert TestClient(app).post('/v1/observability-reliability'+endpoint,json={}).status_code in (401,422,503)
def test_no_transport_or_filesystem_side_effects():
    source=(Path(__file__).resolve().parents[1]/'app/observability_reliability_v1080.py').read_text()
    assert not any(s in source for s in ('requests.post(', 'httpx.post(', 'psycopg.connect(', 'sqlite3.connect(', 'subprocess.run(', 'os.remove(', 'open(', 'smtplib'))
