import time
from html.parser import HTMLParser
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.embeds_v1180 import Embed, render_embed, origin, API_HEADERS, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production';ORIGIN='https://example.org'

def embed(**changes):
    return Embed(**{**dict(synthetic=True,organization_id=ORG,object_ref='embed:fixture',revision='r1',title='Synthetic title',summary='Synthetic summary',canonical_url='https://example.org/source',requested_origin=ORIGIN,source_refs=['source:fixture'],updated_at='2026-10-26T00:00:00Z',expires_at='2026-10-28T00:00:00Z',as_of='2026-10-27T00:00:00Z',rights_reviewed=True,editorial_reviewed=True,privacy_reviewed=True,distribution_reviewed=True),**changes})

def render(**changes):return render_embed(embed(**changes),ORG,[ORIGIN])

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_EMBEDS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    monkeypatch.setenv('SCEC_EMBED_ALLOWED_ORIGINS',ORIGIN)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-embed-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_versioned_offline_contract_and_security_model():
    r=render()
    assert r['schema_version']=='scec.distribution-preview/1' and r['content']['source_refs']==['source:fixture']
    assert all(r[k] is False for k in DISABLED)
    assert not r['public_embed_serving_enabled'] and not r['cors_enabled'] and not r['remote_resources_enabled']
    assert len(r['live_acceptance_gates_pending'])==7
    csp=r['required_future_html_headers']['Content-Security-Policy']
    assert "default-src 'none'" in csp and '; sandbox;' in csp and csp.endswith('frame-ancestors '+ORIGIN)


@pytest.mark.parametrize('value',['https://example.org/','https://example.org/path','https://example.org?x=y','https://example.org#hash','https://example.org:443','http://example.org','https://*.example.org','https://example.org;script-src','https://user@example.org','null'])
def test_noncanonical_or_unsafe_origin(value):
    with pytest.raises(ValueError):origin(value)


def test_operator_origin_policy_not_caller_supplied(client,monkeypatch):
    data=embed().model_dump(mode='json')
    data['requested_origin']='https://example.org.attacker.com'
    assert client.post('/v1/research-embeds/preview',headers=headers(),json=data).status_code==403
    data=embed().model_dump(mode='json')
    h={**headers(),'Origin':'https://attacker.example.com'}
    assert client.post('/v1/research-embeds/preview',headers=h,json=data).status_code==403
    monkeypatch.delenv('SCEC_EMBED_ALLOWED_ORIGINS')
    assert client.post('/v1/research-embeds/preview',headers=headers(),json=data).status_code==503
    monkeypatch.setenv('SCEC_EMBED_ALLOWED_ORIGINS','*')
    assert client.post('/v1/research-embeds/preview',headers=headers(),json=data).status_code==503


@pytest.mark.parametrize('gate',['rights_reviewed','editorial_reviewed','privacy_reviewed','distribution_reviewed'])
def test_incomplete_reviews_never_expose_content(gate):
    r=render(**{gate:False});assert r['content'] is None and r['html_fragment_preview'] is None
    with pytest.raises(ValidationError):embed(**{gate:'yes'})


@pytest.mark.parametrize('changes,reason',[({'suppressed':True},'suppressed'),({'as_of':'2026-10-28T00:00:00Z'},'expired'),({'as_of':'2026-10-25T00:00:00Z'},'not-yet-current'),({'state':'retracted','notice':'Synthetic retraction','notice_source_ref':'source:fixture'},'retracted'),({'state':'withdrawn','notice':'Synthetic withdrawal','notice_source_ref':'source:fixture'},'withdrawn')])
def test_suppression_time_and_notices(changes,reason):
    r=render(**changes);assert reason in r['withheld_reasons'] and r['content'] is None and r['html_fragment_preview'] is None
    assert 'Synthetic title' not in str(r)


def test_corrected_content_preserves_sourced_notice():
    r=render(state='corrected',notice='Synthetic correction',notice_source_ref='source:fixture')
    assert r['content']['notice']=='Synthetic correction' and 'Synthetic correction' in r['html_fragment_preview']
    with pytest.raises(ValidationError):embed(state='corrected')
    with pytest.raises(ValidationError):embed(state='corrected',notice='Synthetic correction',notice_source_ref='source:unknown')


def test_markup_contains_only_fixed_tags_and_escaped_fields():
    r=render(title='Synthetic "quoted" & title',summary="Synthetic 'summary' & text",canonical_url='https://example.org/source?a=1&b=%22')
    markup=r['html_fragment_preview'];assert '&amp;' in markup and '&quot;' in markup and '&#x27;' in markup
    class Tags(HTMLParser):
        def __init__(self):super().__init__();self.tags=[];self.attrs=[]
        def handle_starttag(self,tag,attrs):self.tags.append(tag);self.attrs+=attrs
    parser=Tags();parser.feed(markup)
    assert parser.tags==['article','h1','p','a'] and all(not name.startswith('on') for name,value in parser.attrs)
    with pytest.raises(ValidationError):embed(title='<script>bad</script>')
    with pytest.raises(ValidationError):embed(canonical_url='javascript:alert(1)')


def test_deterministic_policy_and_input_hashes():
    p=embed(source_refs=['source:b','source:a']);r=render_embed(p,ORG,[ORIGIN,'https://other.example.org'])
    data=p.model_dump();data['source_refs'].reverse()
    assert r==render_embed(Embed(**data),ORG,['https://other.example.org',ORIGIN])
    data['revision']='r2';assert r['sha256']!=render_embed(Embed(**data),ORG,[ORIGIN,'https://other.example.org'])['sha256']
    with pytest.raises(ValueError):render_embed(p,OTHER,[ORIGIN])


@pytest.mark.parametrize('path',['/status','/missing'])
def test_api_security_headers_including_errors(client,path):
    r=client.get('/v1/research-embeds'+path,headers=headers())
    for key,value in API_HEADERS.items():assert r.headers[key]==value
    assert 'Access-Control-Allow-Origin' not in r.headers and 'ETag' not in r.headers


def test_auth_validation_tenant_and_default_off(client,monkeypatch):
    url='/v1/research-embeds/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=embed().model_dump(mode='json');assert client.post('/v1/research-embeds/preview',headers=headers(),json=data).status_code==200
    data['summary']='private@example.org';r=client.post('/v1/research-embeds/preview',headers=headers(),json=data)
    assert r.status_code==422 and 'private@example.org' not in r.text and r.headers['Cache-Control']=='no-store, private'
    monkeypatch.setenv('SCEC_EMBEDS_STAGING_ENABLED','0');r=client.get(url,headers=headers());assert r.status_code==503 and r.headers['X-Frame-Options']=='DENY'


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_public_or_outbound_operations(client,action):
    assert client.post('/v1/research-embeds/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/research-embeds/status',headers=headers()).status_code==503
