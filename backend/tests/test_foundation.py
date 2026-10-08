import os
os.environ['SCEC_ENV'] = 'test'
from fastapi.testclient import TestClient
from app.main import app
from app.contracts.models import EngagementObject, Domain, ObjectRef
from app.domains.registry import DOMAINS

client=TestClient(app)

def test_health():
    r=client.get('/health')
    assert r.status_code==200 and r.json()['version']=='8.0.0'

def test_all_domains_unique():
    assert len(DOMAINS)==9 and len({x.name for x in DOMAINS})==9

def test_capabilities():
    r=client.get('/v1/capabilities')
    assert r.status_code==200 and len(r.json())==9

def test_validate_does_not_execute():
    payload={'correlation_id':'c-1','origin':{'system':'legacy','object_type':'case','object_id':'1'}, 'destination':'contacts','subject':{'id':'1','domain':'support','source':{'system':'legacy','object_type':'case','object_id':'1'}}}
    r=client.post('/v1/contracts/handoff/validate',json=payload)
    assert r.status_code==200 and r.json()['action']=='none'

def test_invalid_domain_rejected():
    r=client.post('/v1/contracts/handoff/validate',json={'correlation_id':'c-1','origin':{'system':'a','object_type':'a','object_id':'1'},'destination':'unknown','subject':{'id':'1','domain':'support','source':{'system':'a','object_type':'a','object_id':'1'}}})
    assert r.status_code==422

def test_contract_schema():
    o=EngagementObject(id='a',domain=Domain.support,source=ObjectRef(system='wp',object_type='case',object_id='42'))
    assert o.source.object_id=='42' and o.schema_version=='1.0.0'
