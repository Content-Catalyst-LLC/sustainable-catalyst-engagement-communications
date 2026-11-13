import json
import httpx
import pytest
from app.hubspot import HubSpot

@pytest.mark.parametrize('kind,props', [('contacts',{'email':'press@example.org','firstname':'Synthetic'}),
                                      ('companies',{'domain':'example.org','name':'Synthetic Institute'})])
def test_create_then_deduplicated_update(kind, props):
    saved = []; requests = []
    def mock(req):
        requests.append(req)
        assert req.headers['authorization'] == 'Bearer synthetic-secret'
        data = json.loads(req.content)
        if req.url.path.endswith('/search'):
            return httpx.Response(200, json={'results':saved})
        assert set(data['properties']) == set(props)
        saved[:] = [{'id':'123'}]
        return httpx.Response(201, json={'id':'123'})
    connector=HubSpot('synthetic-secret',transport=httpx.MockTransport(mock))
    try:
        assert connector.sync(kind,props,approved=True).provider_id=='123'
        assert connector.sync(kind,props,approved=True).state=='synced'
        assert [r.method for r in requests]==['POST','POST','POST','PATCH']
    finally: connector.close()

@pytest.mark.parametrize('code,state,retry',[(401,'unauthorized',False),(403,'unauthorized',False),
    (429,'rate_limited',True),(500,'provider_error',True),(409,'conflict',True)])
def test_failures_redacted(code,state,retry):
    c=HubSpot('secret',transport=httpx.MockTransport(lambda r:httpx.Response(code,text='private email secret')))
    result=c.sync('contacts',{'email':'press@example.org'},approved=True)
    assert (result.state,result.retryable)==(state,retry)
    assert 'private' not in repr(result)
    c.close()

def test_excluded_data_and_opt_in_never_make_request():
    def mock(r): raise AssertionError('Unauthorized request')
    c=HubSpot('secret',transport=httpx.MockTransport(mock))
    assert c.sync('contacts',{'email':'press@example.org'},approved=False).state=='not_approved'
    for kind,props in [('newsletters',{'email':'press@example.org'}),('contacts',{'email':'a','research':'private'}),('companies',{'name':'x'})]:
        assert c.sync(kind,props,approved=True).state=='invalid_mapping'
    c.close()

def test_timeout_and_ambiguous_search():
    def timeout(r): raise httpx.ReadTimeout('secret')
    c=HubSpot('secret',transport=httpx.MockTransport(timeout))
    assert c.sync('contacts',{'email':'a'},approved=True).state=='transport_error'
    c.close()
    c=HubSpot('secret',transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'results':[{'id':'1'},{'id':'2'}]})))
    assert c.sync('contacts',{'email':'a'},approved=True).state=='ambiguous_match'
    c.close()
