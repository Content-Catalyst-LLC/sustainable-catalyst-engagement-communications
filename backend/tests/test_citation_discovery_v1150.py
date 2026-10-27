import time
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.citation_discovery_v1150 import Author, Relation, Publication, export, orcid, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS

ORG='00000000-0000-0000-0000-000000000001'
OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production'

def author(**changes):
    return Author(**{**dict(synthetic=True,organization_id=ORG,name='Synthetic Author'),**changes})

def publication(**changes):
    return Publication(**{**dict(synthetic=True,organization_id=ORG,object_ref='citation:synthetic',revision='r1',title='Synthetic methods fixture',authors=[author()],year=2026,canonical_url='https://example.org/research',source_refs=['source:fixture']),**changes})

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_CITATION_STAGING_ENABLED','1')
    monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY)
    monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    token=mint_token(subject='synthetic-citation-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY)
    return {'Authorization':'Bearer '+token,'X-SCEC-Organization-ID':org}


def test_missing_identifier_is_not_fabricated():
    result=export(publication(),ORG)
    assert result['fixture']['doi'] is None
    assert 'DOI' not in result['exports']['csl_json']
    assert 'identifier' not in result['exports']['schema_org_jsonld']
    assert 'DO  -' not in result['exports']['ris'] and 'doi =' not in result['exports']['bibtex']
    assert all(result[k] is False for k in DISABLED)
    assert result['identifier_validation']['registration_checked'] is False
    assert len(result['live_acceptance_gates_pending'])==7


def test_exports_have_correct_bounded_fields():
    p=publication(authors=[author(orcid='0000-0002-1825-0097')],ror='https://ror.org/03yrm5c26')
    result=export(p,ORG)
    assert result['exports']['csl_json']['issued']['date-parts']==[[2026]]
    assert result['exports']['schema_org_jsonld']['author'][0]['sameAs']=='https://orcid.org/0000-0002-1825-0097'
    assert result['exports']['ris'].endswith('ER  - \r\n')
    assert result['identifier_validation']['ror']=='url-shape-only'
    digest=result.pop('sha256')
    assert digest==hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


@pytest.mark.parametrize('value',['0000-0002-1825-0097','0000-0001-5109-3700','0000-0002-1694-233X'])
def test_official_orcid_checksum_examples(value):
    assert orcid(value)==value


@pytest.mark.parametrize('value',['0000-0002-1825-0098','0000-0002-1694-233x','https://orcid.org/0000-0002-1825-0097','0000000218250097'])
def test_invalid_orcid(value):
    with pytest.raises(ValidationError):author(orcid=value)


@pytest.mark.parametrize('doi',['https://doi.org/10.1234/example','fake','10.123/a','10.12345/','10.1234/a\nER  - ','10.1234/a b'])
def test_invalid_or_unsupported_doi_syntax(doi):
    with pytest.raises(ValidationError):publication(doi=doi)


def test_supplied_doi_preserved_without_existence_claim():
    # Crossref's public documentation DOI example, not assigned to real research here.
    value='10.1002/(SICI)1097-0142(19990301)85:5<950::AID-CNCR10>3.0.CO;2-9'
    # Legacy angle-bracket forms are deliberately outside our conservative subset.
    with pytest.raises(ValidationError):publication(doi=value)
    p=publication(doi='10.5555/12345678')
    r=export(p,ORG)
    assert r['exports']['csl_json']['DOI']==p.doi
    assert r['identifier_validation']['doi']=='conservative-syntax-only'
    assert r['identifier_validation']['registration_checked'] is False


@pytest.mark.parametrize('url',['http://example.org/a','https://localhost/a','https://127.0.0.1/a','https://[::1]/a','https://user:pass@example.org/a','https://example.org:1234/a','https://example.org/a\nAU  - injected','javascript:alert(1)','https://example.org/<script>'])
def test_unsafe_urls(url):
    with pytest.raises(ValidationError):publication(canonical_url=url)


@pytest.mark.parametrize('title',['Synthetic\nER  - injection','Synthetic\rAU  - bad','Synthetic\x00bad','<script>x</script>'])
def test_text_and_ris_injection(title):
    with pytest.raises(ValidationError):publication(title=title)


def test_bibtex_special_characters_cannot_close_fields():
    result=export(publication(title='Synthetic }{ & % $ # _ ~ ^ \\ title'),ORG)['exports']['bibtex']
    assert r'\}\{' in result and r'\&' in result and r'\textbackslash{}' in result


@pytest.mark.parametrize('kind',['correction','retraction','update'])
def test_explicit_relations_are_preserved_without_inference(kind):
    relation=Relation(synthetic=True,organization_id=ORG,kind=kind,url='https://example.org/notice',source_ref='source:fixture')
    r=export(publication(relations=[relation]),ORG)
    assert r['relations'][0]['kind']==kind
    assert r['relations_embedded_in_exports'] is False
    assert r['fixture']['source_refs']==['source:fixture']
    assert not r['source_fetch_performed']


def test_duplicate_or_cross_tenant_or_unprovenanced_metadata_rejected():
    with pytest.raises(ValidationError):publication(authors=[author(),author()])
    with pytest.raises(ValidationError):publication(authors=[author(organization_id=OTHER)])
    with pytest.raises(ValidationError):publication(source_refs=['source:fixture','source:fixture'])
    relation=Relation(synthetic=True,organization_id=ORG,kind='update',url='https://example.org/notice',source_ref='source:fixture')
    with pytest.raises(ValidationError):publication(relations=[relation,relation])
    with pytest.raises(ValidationError):publication(relations=[relation],source_refs=['source:other'])
    with pytest.raises(ValueError):export(publication(),OTHER)


def test_revision_and_provenance_change_hash():
    original=export(publication(),ORG)['sha256']
    assert original!=export(publication(revision='r2'),ORG)['sha256']
    assert original!=export(publication(source_refs=['source:other']),ORG)['sha256']


def test_http_authorization_default_off_and_no_validation_reflection(client,monkeypatch):
    url='/v1/citation-discovery/status'
    assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    assert client.get(url,headers=headers(OTHER)).status_code==403
    data=publication().model_dump(mode='json')
    assert client.post('/v1/citation-discovery/preview',headers=headers(),json=data).status_code==200
    data['title']='private@example.org'
    response=client.post('/v1/citation-discovery/preview',headers=headers(),json=data)
    assert response.status_code==422 and data['title'] not in response.text
    monkeypatch.setenv('SCEC_CITATION_STAGING_ENABLED','0')
    assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_live_actions_even_for_admin(client,action):
    assert client.post('/v1/citation-discovery/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_every_dangerous_flag_blocks_preview(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1')
    assert client.get('/v1/citation-discovery/status',headers=headers()).status_code==503
