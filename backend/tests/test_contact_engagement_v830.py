import os
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.contracts.canonical import Organization, Contact, Inquiry, EngagementEvent
from app.contact_service import serialize, config, get_tenant
from fastapi import HTTPException
from app.persistence.audit import audit_events
from app.persistence.models import metadata

def test_models_and_audit():
    assert audit_events.name in metadata.tables
    assert audit_events.c.organization_id.foreign_keys

def test_tenant_contract():
    tenant=uuid4(); other=uuid4()
    item=Contact(organization_id=tenant,display_name='Example')
    assert serialize(item,tenant)['display_name']=='Example'
    try:serialize(item,other); assert False
    except HTTPException as e: assert e.status_code==403

def test_missing_org():
    try:serialize(Contact(display_name='A'),uuid4());assert False
    except HTTPException as e:assert e.status_code==403

def test_org_bootstrap():
    tenant=uuid4()
    org=Organization(id=tenant,name='Test',slug='test')
    assert serialize(org,tenant)['organization_id']==str(tenant)

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SCEC_PERSISTENCE_ENABLED',raising=False)
    try:config();assert False
    except HTTPException as e: assert e.status_code==503

def test_forged_tenant(monkeypatch):
    tenant=uuid4(); other=uuid4()
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    monkeypatch.setenv('SCEC_DATABASE_URL','postgresql+psycopg://a:b@127.0.0.1/scec_engagement_v820')
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(tenant))
    try:get_tenant(str(other)); assert False
    except HTTPException as e: assert e.status_code==403

def test_disallowed_database(monkeypatch):
    monkeypatch.setenv('SCEC_PERSISTENCE_ENABLED','1')
    monkeypatch.setenv('SCEC_DATABASE_URL','postgresql+psycopg://a:b@127.0.0.1/wordpress')
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',str(uuid4()))
    try:config();assert False
    except HTTPException as e:assert e.status_code==503

def test_disabled_endpoint():
    r=TestClient(app).get('/v1/engagement/contacts',headers={'X-SCEC-Organization-ID':str(uuid4())})
    assert r.status_code in (401,503)
