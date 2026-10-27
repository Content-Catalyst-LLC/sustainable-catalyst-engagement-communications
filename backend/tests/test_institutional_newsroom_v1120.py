from datetime import datetime,timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from app.institutional_newsroom_v1120 import NewsroomEntry,NewsroomPreview,assess,ANNOUNCEMENT_KINDS,STATES,BLOCKED_ACTIONS
from app.main import app

def item(**overrides):
    values=dict(announcement_ref='article-123',revision='v1',kind='research-release',headline='Test research',summary='Synthetic description',canonical_url='https://example.org/research/123',updated_at=datetime(2026,10,17,tzinfo=timezone.utc),source_refs=['source-123'])
    values.update(overrides);return NewsroomEntry(**values)
def payload(**changes):
    values=dict(newsroom_title='Synthetic Newsroom',newsroom_url='https://example.org/news',entries=[item()]);values.update(changes)
    return NewsroomPreview(**values)
def test_all_types_and_states():
    assert len(ANNOUNCEMENT_KINDS)==5 and len(STATES)==4
    for kind in ANNOUNCEMENT_KINDS:
        for state in STATES:assert item(kind=kind,editorial_state=state)
def test_fail_closed():
    x=assess(payload(),str(uuid4()))
    assert not any(x[k] for k in ['actual_publication_enabled','outbound_communications_enabled','persisted','source_fetch_performed','federation_enabled','human_login_enabled','deletion_enabled','production_certified'])
    assert len(x['live_acceptance_gates_pending'])==7
    assert x['entries'][0]['review_gates']['production-acceptance'] is False
@pytest.mark.parametrize('field', ['rights_reviewed','editorial_reviewed','source_integrity_reviewed','privacy_reviewed','institutional_approved'])
def test_individual_gate(field):
    e=item(**{field:False});g=assess(payload(entries=[e]),str(uuid4()))['entries'][0]
    assert g['editorial_review_complete'] is False

def test_all_reviews_still_never_publish():
    e=item(rights_reviewed=True,editorial_reviewed=True,source_integrity_reviewed=True,privacy_reviewed=True,institutional_approved=True,editorial_state='approved-preview')
    g=assess(payload(entries=[e]),str(uuid4()))
    assert g['entries'][0]['editorial_review_complete'] is True
    assert g['entries'][0]['publication_authorized'] is False
@pytest.mark.parametrize('bad', ['http://example.org/news','https://localhost/news','https://example.org/news#fragment','https://name:pass@example.org/news'])
def test_unsafe_urls(bad):
    with pytest.raises(ValidationError):item(canonical_url=bad)
def test_no_extra_fields():
    with pytest.raises(ValidationError):item(recipient_email='x@example.org')
def test_no_naive_datetime():
    with pytest.raises(ValidationError):item(updated_at=datetime(2026,10,17))
def test_no_repeat_revisions():
    with pytest.raises(ValidationError):payload(entries=[item(),item()])
def test_no_repeated_sources():
    with pytest.raises(ValidationError):item(source_refs=['source-123','source-123'])
def test_empty_entries_rejected():
    with pytest.raises(ValidationError):payload(entries=[])
def test_deterministic_reorder_and_source_order():
    a=item();b=item(announcement_ref='article-456',source_refs=['source-222','source-111'])
    tenant=str(uuid4())
    x=assess(payload(entries=[a,b]),tenant)
    assert x['sha256']==assess(payload(entries=[b,a]),tenant)['sha256']
def test_cross_tenant_fingerprints():
    assert assess(payload(),str(uuid4()))['sha256']!=assess(payload(),str(uuid4()))['sha256']
def test_invalid_tenant_uuid():
    with pytest.raises(ValueError):assess(payload(),'invalid')
def test_portal_disabled():
    c=TestClient(app)
    r=c.get('/v1/institutional-newsroom/status')
    assert r.status_code in (401,403,503)
    for action in BLOCKED_ACTIONS:
        r=c.post('/v1/institutional-newsroom/'+action)
        assert r.status_code in (401,403,503)
def test_main_version():
    assert app.version=='11.6.0'
