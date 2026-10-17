from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.support_service import TRANSITIONS, CaseTransition, SupportFeedback, create_case, transition_case
from app.contracts.canonical import Case
from app.contact_service import ALLOWED

def test_health_v840():
 assert TestClient(app).get('/health').json()['version']=='10.6.0'

def test_disabled_support_rejected():
 assert TestClient(app).get('/v1/support/cases').status_code in (401,503)

def test_case_schema_and_classification():
 c=Case(title='Cannot log in',organization_id=uuid4(),product_key='library')
 assert c.status=='open'
 assert c.product_key=='library'

def test_transition_contract():
 assert TRANSITIONS['closed']==set()
 assert 'triaged' in TRANSITIONS['open']
 assert 'closed' not in TRANSITIONS['in_progress']
 with pytest.raises(Exception): CaseTransition(status='invalid',actor_ref='operator')
 with pytest.raises(Exception): SupportFeedback(actor_ref='operator',note='')

def test_generic_create_disallows_cases():
 assert 'cases' not in ALLOWED

def test_migration_chain():
 from importlib import util
 from pathlib import Path
 f=Path(__file__).parents[1]/'alembic/versions/840_001_support_history.py'
 spec=util.spec_from_file_location('migration840',f);module=util.module_from_spec(spec);spec.loader.exec_module(module)
 assert module.revision=='840_001' and module.down_revision=='830_001'
