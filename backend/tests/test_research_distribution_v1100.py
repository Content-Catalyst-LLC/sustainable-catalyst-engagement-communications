import pytest
from uuid import uuid4
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.research_distribution_v1100 import (DistributionPreview, DISTRIBUTION_TARGETS,OBJECT_TYPES,
    REQUIRED_REVIEW,BLOCKED_ACTIONS,preview,safety_state)
from app.production_acceptance_v1090 import GATES
TENANT=str(uuid4())
def item(**kwargs):
    data=dict(object_ref='research-test',revision='v1',object_kind='research-article',
        targets=['rss','atom'],source_refs=['source-a','source-b'])
    data.update(kwargs)
    return DistributionPreview(**data)
def test_app_version_and_registry():
    assert app.version=='11.9.0'
    assert len(DISTRIBUTION_TARGETS)==6 and len(OBJECT_TYPES)==5
    assert len(REQUIRED_REVIEW)==6 and len(BLOCKED_ACTIONS)==7
@pytest.mark.parametrize('target',DISTRIBUTION_TARGETS)
def test_targets_are_preview_only(target):
    x=preview(item(targets=[target]),TENANT)
    assert x['requested_targets']==[target]
    assert not x['publication_authorized'] and not x['outbound_communications_enabled']
@pytest.mark.parametrize('kind',OBJECT_TYPES)
def test_object_types(kind):
    assert preview(item(object_kind=kind),TENANT)['object_kind']==kind
@pytest.mark.parametrize('field',('publication_authorized','actual_publication_enabled','actual_syndication_enabled','outbound_communications_enabled','persisted','live_sources_fetched','federation_enabled'))
def test_fail_closed(field):assert preview(item(),TENANT)[field] is False
def test_every_gate_can_be_reviewed_but_cannot_activate():
    x=preview(item(rights_basis='open-license',editorial_reviewed=True,privacy_reviewed=True,
         source_integrity_reviewed=True,distribution_approved=True),TENANT)
    assert x['human_review_complete']
    assert x['review_gates']['production_acceptance'] is False
    assert x['live_acceptance_gates_pending']==list(GATES)
    assert x['publication_authorized'] is False
@pytest.mark.parametrize('field,value',(('targets',['rss','rss']),('source_refs',['same-ref','same-ref']),
    ('object_ref','xx'),('source_refs',['email@example.com']),('object_kind','unknown'),('targets',['webhook'])))
def test_invalid_manifest_data(field,value):
    with pytest.raises(ValidationError):DistributionPreview(**{**item().model_dump(),field:value})
@pytest.mark.parametrize('field',('email','recipient','message','payload','auth_token','publish_url'))
def test_no_personal_data_or_transport_parameters(field):
    with pytest.raises(ValidationError):DistributionPreview(**{**item().model_dump(),field:'secret'})
def test_deterministic_fingerprint():
    a=preview(item(),TENANT);b=preview(item(targets=['atom','rss'],source_refs=['source-b','source-a']),TENANT)
    c=preview(item(revision='v2'),TENANT)
    assert a['manifest_sha256']==b['manifest_sha256']!=c['manifest_sha256']
def test_tenant_bound_fingerprint_and_noncanonical_rejection():
    assert preview(item(),TENANT)['manifest_sha256']!=preview(item(),str(uuid4()))['manifest_sha256']
    with pytest.raises(ValueError):preview(item(),TENANT.upper())
def test_safety_flags_fail_closed(monkeypatch):
    from app.wordpress_bridge_certification_v1050 import DANGER_FLAGS
    for flag in DANGER_FLAGS: monkeypatch.setenv(flag,'0')
    assert safety_state()
    for flag in DANGER_FLAGS:
        monkeypatch.setenv(flag,'1');assert not safety_state();monkeypatch.setenv(flag,'0')
@pytest.mark.parametrize('path',('/status','/manifest-preview')+tuple('/'+s for s in BLOCKED_ACTIONS))
def test_http_default_blocked(monkeypatch,path):
    monkeypatch.setenv('SCEC_DISTRIBUTION_STAGING_ENABLED','0')
    if path=='/status':res=TestClient(app).get('/v1/research-distribution'+path)
    else:res=TestClient(app).post('/v1/research-distribution'+path,json={})
    assert res.status_code in (401,422,503)
def test_no_side_effect_apis():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[1]/'app/research_distribution_v1100.py').read_text()
    assert not any(x in source for x in ('httpx.post(', 'requests.post(', 'subprocess.run(', 'sqlite3.connect(', 'psycopg.connect(', 'smtplib.SMTP(', 'wp_remote_post(', 'os.remove('))
