from uuid import uuid4
from importlib import util
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.advisory_service import TRANSITIONS, ApprovalRequest, ApprovalDecision, AdvisoryTransition, create_engagement, request_approval
from app.contracts.canonical import AdvisoryEngagement
from app.contact_service import ALLOWED

def test_version():
    assert TestClient(app).get('/health').json()['version']=='11.4.0'

def test_production_disabled_and_auth():
    assert TestClient(app).get('/v1/advisory/engagements').status_code in (401,503)

def test_advisory_api_registered():
    paths={r.path for r in app.routes}
    assert '/v1/advisory/engagements/{engagement_id}/approvals/{approval_id}/decision' in paths
    assert '/v1/advisory/engagements/{engagement_id}/history' in paths

def test_no_generic_advisory_bypass():
    assert 'advisory_engagements' not in ALLOWED

def test_transition_contract():
    assert 'active' not in TRANSITIONS['proposed']
    assert 'active' in TRANSITIONS['paused']
    assert TRANSITIONS['completed']==set()
    with pytest.raises(Exception):AdvisoryTransition(status='proposed',actor_ref='x')

def test_approval_contract():
    assert ApprovalRequest(actor_ref='requester').actor_ref=='requester'
    assert ApprovalDecision(decision='approved',actor_ref='reviewer').decision=='approved'
    with pytest.raises(Exception):ApprovalDecision(decision='maybe',actor_ref='a')

def test_engagement_schema():
    obj=AdvisoryEngagement(title='Institutional advisory',organization_id=uuid4())
    assert obj.status=='proposed'

def test_migration_chain():
    f=Path(__file__).parents[1]/'alembic/versions/850_001_advisory_workflows.py'
    spec=util.spec_from_file_location('migration850',f);m=util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.revision=='850_001' and m.down_revision=='840_001'

class DummySession:
    def begin(self):
        return self
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,*args):return self
    def first(self):return None

def test_missing_organization_rejected():
    tenant=uuid4()
    with pytest.raises(HTTPException) as e:
        create_engagement({'title':'Example','organization_id':str(tenant)},tenant,DummySession())
    assert e.value.status_code==422

def test_payload_mismatch_rejected_before_sql():
    with pytest.raises(HTTPException) as e:
        create_engagement({'title':'Example','organization_id':str(uuid4())},uuid4(),DummySession())
    assert e.value.status_code==403
