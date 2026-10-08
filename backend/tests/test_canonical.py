import os
os.environ['SCEC_ENV']='test'
from uuid import uuid4
from datetime import datetime,timezone,timedelta
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.contracts.canonical import MODEL_REGISTRY, Contact, Classification, Submission, Case, LegacyIdentity, Inquiry, Organization, Assessment, Newsletter
client=TestClient(app)

@pytest.mark.parametrize('name,model',list(MODEL_REGISTRY.items()))
def test_schema_generated(name,model):
    assert model.model_json_schema()['title']
    r=client.get(f'/v1/contracts/canonical/{name}/schema')
    assert r.status_code==200

def test_registry_read_only():
    r=client.get('/v1/contracts/canonical')
    assert r.status_code==200 and r.json()['persistence']=='none' and len(r.json()['models'])==12
    assert client.post('/v1/contracts/canonical',json={}).status_code==405
    assert client.get('/v1/contracts/canonical/missing/schema').status_code==404

def test_contact_private_and_consent_default_off():
    c=Contact(display_name='Example')
    assert c.marketing_consent is False
    with pytest.raises(ValidationError): Contact(display_name='Example',classification='public')

def test_submission_restricts_access():
    valid=Submission(form_id=uuid4(),form_revision=1,payload_ref='blob:opaque')
    assert valid.classification==Classification.confidential
    with pytest.raises(ValidationError): Submission(form_id=uuid4(),form_revision=1,payload_ref='blob:x',classification='public')

def test_legacy_identity_and_extra_fields():
    item=Case(title='Example',legacy_identity=LegacyIdentity(system='product_support_feedback',object_type='ticket',external_id='42'))
    assert item.legacy_identity.external_id=='42'
    with pytest.raises(ValidationError): Case(title='Example',secret='unrecognized')

def test_temporal_invariants():
    now=datetime.now(timezone.utc)
    with pytest.raises(ValidationError): Inquiry(subject='Example',created_at=now,updated_at=now-timedelta(days=1))
    with pytest.raises(ValidationError): Inquiry(subject='Example',created_at=now.replace(tzinfo=None))

def test_slug_validation():
    assert Organization(name='Research Lab',slug='research-lab').slug=='research-lab'
    with pytest.raises(ValidationError): Organization(name='Lab',slug='Bad Slug')

def test_default_assessment_review():
    assert Assessment(title='Evaluation').human_review_required is True

def test_schema_contract_version():
    assert Newsletter(title='Research').schema_version=='8.1.0'
