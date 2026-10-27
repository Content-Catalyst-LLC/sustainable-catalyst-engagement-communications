"""Offline synthetic scholarly metadata; no indexing, lookup or registration."""
import re
import ipaddress
from urllib.parse import urlsplit
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, plain, opaque
from .offline_staging import scope, seal

router = APIRouter(prefix='/v1/citation-discovery', tags=['citation-discovery-staging'], route_class=SyntheticPreviewRoute)
_scope = scope('SCEC_CITATION_STAGING_ENABLED')
BLOCKED_ACTIONS = ('register', 'index', 'publish', 'send', 'activate', 'delete', 'federate')


def text(value):
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Control characters forbidden')
    return plain(value)


def public_url(value):
    """Conservative offline hostname check, never DNS resolution or a fetch."""
    if any(c.isspace() or ord(c) < 32 for c in value) or any(c in value for c in '<>"\\'):
        raise ValueError('Unsafe URL')
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Public HTTPS URL required')
    host = p.hostname.lower()
    if not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)*', host) or '.' not in host or host.endswith(('.localhost', '.local', '.internal', '.test', '.invalid')):
        raise ValueError('Public hostname required')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('Literal addresses forbidden')
    return value


def orcid(value):
    if not re.fullmatch(r'[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]' , value):
        raise ValueError('ORCID format')
    digits = value.replace('-', '')
    total = 0
    for digit in digits[:15]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    if digits[-1] != ('X' if check == 10 else str(check)):
        raise ValueError('ORCID checksum')
    return value


class Author(Fixture):
    name: str = Field(min_length=1, max_length=120)
    orcid: str | None = Field(default=None, max_length=19)

    @field_validator('name')
    @classmethod
    def name_text(cls, v): return text(v)

    @field_validator('orcid')
    @classmethod
    def identifier(cls, v): return orcid(v) if v is not None else None


class Relation(Fixture):
    kind: Literal['correction', 'retraction', 'update']
    url: str = Field(min_length=10, max_length=500)
    source_ref: str = Field(min_length=3, max_length=96)

    @field_validator('url')
    @classmethod
    def url_check(cls, v): return public_url(v)

    @field_validator('source_ref')
    @classmethod
    def source(cls, v): return opaque(v)


class Publication(Fixture):
    publication_type: Literal['journal-article'] = 'journal-article'
    object_ref: str = Field(min_length=3, max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    title: str = Field(min_length=1, max_length=300)
    authors: list[Author] = Field(min_length=1, max_length=20)
    year: int = Field(strict=True, ge=1600, le=2200)
    canonical_url: str = Field(min_length=10, max_length=500)
    doi: str | None = Field(default=None, max_length=200)
    ror: str | None = Field(default=None, max_length=25)
    source_refs: list[str] = Field(min_length=1, max_length=20)
    relations: list[Relation] = Field(default_factory=list, max_length=20)

    @field_validator('object_ref')
    @classmethod
    def reference(cls, v): return opaque(v)

    @field_validator('title')
    @classmethod
    def title_text(cls, v): return text(v)

    @field_validator('canonical_url')
    @classmethod
    def url_check(cls, v): return public_url(v)

    @field_validator('doi')
    @classmethod
    def doi_check(cls, v):
        if v is not None and not re.fullmatch(r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+', v):
            raise ValueError('Conservative DOI syntax required')
        return v

    @field_validator('ror')
    @classmethod
    def ror_check(cls, v):
        if v is not None and not re.fullmatch(r'https://ror\.org/[0-9a-z]{9}', v):
            raise ValueError('ROR URL shape required; checksum not checked')
        return v

    @field_validator('source_refs')
    @classmethod
    def sources(cls, v):
        if len(v) != len(set(v)): raise ValueError('Duplicate source')
        return [opaque(x) for x in v]

    @model_validator(mode='after')
    def bounded(self):
        if any(x.organization_id != self.organization_id for x in [*self.authors, *self.relations]):
            raise ValueError('Cross-tenant metadata')
        if len({(a.name, a.orcid) for a in self.authors}) != len(self.authors):
            raise ValueError('Duplicate author')
        if len({(r.kind, r.url) for r in self.relations}) != len(self.relations):
            raise ValueError('Duplicate relation')
        if any(r.source_ref not in self.source_refs for r in self.relations):
            raise ValueError('Unregistered relation source')
        return self


def bib(value):
    escapes = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(escapes.get(c, c) for c in value)


def export(publication: Publication, tenant: str):
    if publication.organization_id != tenant: raise ValueError('Tenant mismatch')
    p = publication
    csl = {'id': p.object_ref, 'type': 'article-journal', 'title': p.title, 'author': [{'literal': a.name} for a in p.authors], 'issued': {'date-parts': [[p.year]]}, 'URL': p.canonical_url}
    schema = {'@context': 'https://schema.org', '@type': 'ScholarlyArticle', 'headline': p.title, 'url': p.canonical_url, 'datePublished': str(p.year), 'author': [{'@type': 'Person', 'name': a.name, **({'sameAs': 'https://orcid.org/' + a.orcid} if a.orcid else {})} for a in p.authors]}
    fields = [('title', p.title), ('year', str(p.year)), ('url', p.canonical_url)]
    ris = ['TY  - JOUR', 'TI  - ' + p.title, *['AU  - ' + a.name for a in p.authors], 'PY  - ' + str(p.year), 'UR  - ' + p.canonical_url]
    if p.doi:
        csl['DOI'] = p.doi
        schema['identifier'] = {'@type': 'PropertyValue', 'propertyID': 'DOI', 'value': p.doi}
        fields.append(('doi', p.doi)); ris.append('DO  - ' + p.doi)
    author_field = '  author = {' + ' and '.join('{' + bib(a.name) + '}' for a in p.authors) + '}'
    bibtex = '@article{syntheticpreview,\n' + author_field + ',\n' + ',\n'.join('  ' + k + ' = {' + bib(v) + '}' for k, v in fields) + '\n}\n'
    normalized = p.model_dump(mode='json')
    normalized['source_refs'].sort()
    normalized['relations'].sort(key=lambda r: (r['kind'], r['url']))
    return seal({'mode': 'offline-synthetic-citation-preview', 'fixture': normalized,
                 'exports': {'bibtex': bibtex, 'ris': '\r\n'.join([*ris, 'ER  - ', '']), 'csl_json': csl, 'schema_org_jsonld': schema},
                 'relations': normalized['relations'], 'relations_embedded_in_exports': False,
                 'identifier_validation': {'doi': 'conservative-syntax-only', 'orcid': 'format-and-checksum-only', 'ror': 'url-shape-only', 'registration_checked': False},
                 'indexing_registration_enabled': False, 'author_names': 'synthetic-fixture-only'}, tenant, '11.5.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode': 'offline-synthetic-citation-preview', 'indexing_registration_enabled': False}, str(tenant), '11.5.0')


@router.post('/preview')
def preview(payload: Publication, tenant=Depends(_scope)):
    try: return export(payload, str(tenant))
    except ValueError: raise HTTPException(422, 'Fixture tenant mismatch') from None


@router.post('/register')
@router.post('/index')
@router.post('/publish')
@router.post('/send')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503, 'Live discovery operations disabled')
