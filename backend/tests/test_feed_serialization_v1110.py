import json
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from xml.etree import ElementTree as ET
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import app
from app.feed_serialization_v1110 import FeedEntry,FeedPreview,FORMATS,render,BLOCKED_ACTIONS

TENANT=str(uuid4())
def entry(**overrides):
    data=dict(object_ref='synthetic-123',revision='v1',title='Synthetic research',summary='A safe abstract',canonical_url='https://example.org/research/123',updated_at=datetime(2026,10,17,tzinfo=timezone.utc),source_refs=['source-abc'])
    data.update(overrides);return FeedEntry(**data)
def feed(fmt='rss',**overrides):
    data=dict(format=fmt,feed_title='Research',feed_description='Synthetic discoveries',home_url='https://example.org/',feed_url='https://example.org/feed',entries=[entry()]);data.update(overrides);return FeedPreview(**data)

def test_current_version():assert app.version=='12.3.0'
@pytest.mark.parametrize('fmt',FORMATS)
def test_serialized_formats(fmt):
    x=render(feed(fmt),TENANT)
    assert x['release']=='11.1.0' and x['entry_count']==1 and x['sha256']
    if fmt=='json-feed':
        doc=json.loads(x['content_preview']);assert doc['version']=='https://jsonfeed.org/version/1.1';assert doc['items'][0]['_source_refs']==['source-abc']
    else:
        root=ET.fromstring(x['content_preview']);assert root.tag in ('rss','{http://www.w3.org/2005/Atom}feed')
@pytest.mark.parametrize('fmt',FORMATS)
def test_stable_reordering(fmt):
    a=entry();b=entry(object_ref='synthetic-999',canonical_url='https://example.org/research/999')
    x=render(feed(fmt,entries=[a,b]),TENANT)
    y=render(feed(fmt,entries=[b,a]),TENANT)
    assert x['sha256']==y['sha256']
@pytest.mark.parametrize('fmt',FORMATS)
def test_tenant_binding(fmt):assert render(feed(fmt),TENANT)['sha256']!=render(feed(fmt),str(uuid4()))['sha256']
@pytest.mark.parametrize('field',('publication_authorized','actual_syndication_enabled','outbound_communications_enabled','persisted','source_fetch_performed','federation_enabled','production_certified'))
def test_fail_closed(field):assert render(feed(),TENANT)[field] is False
@pytest.mark.parametrize('url',('http://example.org/x','https://localhost/x','https://example.org/path#fragment','https://user:pass@example.org/x','https://example.org:8080/x'))
def test_reject_unsafe_urls(url):
    with pytest.raises(ValidationError):entry(canonical_url=url)
@pytest.mark.parametrize('kwargs',({'updated_at':datetime(2026,10,17)}, {'source_refs':['x@y.com']}, {'source_refs':['same-abc','same-abc']}, {'title':''}))
def test_invalid_entry(kwargs):
    with pytest.raises(ValidationError):entry(**kwargs)
def test_duplicate_revision_rejected():
    with pytest.raises(ValidationError):feed(entries=[entry(),entry()])
def test_reject_unexpected_private_fields():
    with pytest.raises(ValidationError):feed(recipient='someone@example.org')
    with pytest.raises(ValidationError):entry(token='secret')
@pytest.mark.parametrize('path',('/status','/preview')+tuple('/'+s for s in BLOCKED_ACTIONS))
def test_default_http_closed(path,monkeypatch):
    monkeypatch.setenv('SCEC_DISTRIBUTION_STAGING_ENABLED','0')
    response=TestClient(app).get('/v1/research-feeds'+path) if path=='/status' else TestClient(app).post('/v1/research-feeds'+path,json={})
    assert response.status_code in (401,422,503)
def test_noncanonical_tenant_rejected():
    with pytest.raises(ValueError):render(feed(),TENANT.upper())
