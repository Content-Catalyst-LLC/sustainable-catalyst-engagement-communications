"""Frozen synthetic lineage contracts, not an external provenance attestation."""
import hashlib
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, Field, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/communication-objects',tags=['communications-operations-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_OBJECTS_STAGING_ENABLED')
BLOCKED_ACTIONS=('commit','publish','send','activate','delete','federate')
RELEASES={'research':'11.0.0','feed':'11.1.0','announcement':'11.2.0','alert':'11.3.0','press':'11.4.0','citation':'11.5.0','event':'11.6.0','partnership':'11.7.0','embed':'11.8.0','audience':'11.9.0'}
HASH_KINDS={kind:('source-manifest' if kind=='research' else 'serialized-content' if kind=='feed' else 'input-projection' if kind=='alert' else 'envelope') for kind in RELEASES}


class FrozenFixture(Fixture):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,frozen=True)


class EvidencePointer(FrozenFixture):
    node_ref: str = Field(min_length=3,max_length=96)
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @field_validator('node_ref')
    @classmethod
    def reference(cls,v):return opaque(v)


class EvidenceFacts(FrozenFixture):
    node_ref: str = Field(min_length=3,max_length=96)
    kind: Literal['research','announcement','feed','alert','press','citation','event','partnership','embed','audience']
    research_ref: str = Field(min_length=3,max_length=96)
    research_revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    artifact_ref: str = Field(min_length=3,max_length=96)
    artifact_revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    source_release: str = Field(pattern=r'^11\.[0-9]\.0$')
    source_hash_kind: Literal['source-manifest','serialized-content','input-projection','envelope']
    source_digest: str = Field(pattern=r'^[a-f0-9]{64}$')
    source_refs: tuple[str,...] = Field(min_length=1,max_length=20)
    parents: tuple[EvidencePointer,...] = Field(default_factory=tuple,max_length=20)

    @field_validator('node_ref','research_ref','artifact_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('source_refs')
    @classmethod
    def sources(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Repeated source')
        return tuple(sorted(opaque(x) for x in v))

    @field_validator('parents')
    @classmethod
    def parent_order(cls,v):
        if len({p.node_ref for p in v})!=len(v):raise ValueError('Repeated parent')
        return tuple(sorted(v,key=lambda p:p.node_ref))

    @model_validator(mode='after')
    def semantics(self):
        if self.source_release!=RELEASES[self.kind] or self.source_hash_kind!=HASH_KINDS[self.kind]:raise ValueError('Source release or hash meaning mismatch')
        if self.kind=='research':
            if self.parents or self.artifact_ref!=self.research_ref or self.artifact_revision!=self.research_revision:raise ValueError('Invalid research root')
        elif not self.parents:raise ValueError('Non-root evidence requires a parent')
        if any(p.organization_id!=self.organization_id for p in self.parents):raise ValueError('Cross-tenant pointer')
        return self


def facts_digest(facts:EvidenceFacts):
    return hashlib.sha256(json.dumps(facts.model_dump(mode='json'),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


class EvidenceNode(EvidenceFacts):
    evidence_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def check_digest(self):
        facts=EvidenceFacts(**self.model_dump(exclude={'evidence_sha256'}))
        if self.evidence_sha256!=facts_digest(facts):raise ValueError('Evidence integrity mismatch')
        return self


def make_node(**values):
    """Offline fixture helper; caller-supplied source_digest stays unverified."""
    facts=EvidenceFacts(**values)
    return EvidenceNode(**facts.model_dump(),evidence_sha256=facts_digest(facts))


class CommunicationObject(FrozenFixture):
    schema_version: Literal['scec.communication-object/1']='scec.communication-object/1'
    communication_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    root_node_ref: str = Field(min_length=3,max_length=96)
    nodes: tuple[EvidenceNode,...] = Field(min_length=1,max_length=40)

    @field_validator('communication_ref','root_node_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @model_validator(mode='after')
    def graph(self):
        refs={n.node_ref:n for n in self.nodes}
        if len(refs)!=len(self.nodes):raise ValueError('Repeated evidence node')
        if len({(n.kind,n.artifact_ref,n.artifact_revision) for n in self.nodes})!=len(self.nodes):raise ValueError('Repeated artifact revision')
        if self.root_node_ref not in refs or refs[self.root_node_ref].kind!='research' or sum(n.kind=='research' for n in self.nodes)!=1:raise ValueError('Exactly one declared research root required')
        root=refs[self.root_node_ref]
        for node in self.nodes:
            if node.organization_id!=self.organization_id:raise ValueError('Cross-tenant node')
            if (node.research_ref,node.research_revision)!=(root.research_ref,root.research_revision):raise ValueError('Cross-research lineage')
            if not set(node.source_refs).issubset(root.source_refs):raise ValueError('Unregistered root provenance')
            for pointer in node.parents:
                if pointer.node_ref not in refs:raise ValueError('Orphan lineage pointer')
                if pointer.evidence_sha256!=refs[pointer.node_ref].evidence_sha256:raise ValueError('Stale parent digest')
        # Kahn traversal detects cycles without recursion; every child has a
        # parent and only the root can have none, so this also proves reachability.
        done=set()
        while len(done)<len(refs):
            available={ref for ref,n in refs.items() if ref not in done and all(p.node_ref in done for p in n.parents)}
            if not available:raise ValueError('Cyclic or unreachable lineage')
            done.update(available)
        return self


def preview_object(obj:CommunicationObject,tenant:str):
    if obj.organization_id!=tenant:raise ValueError('Tenant mismatch')
    normalized=obj.model_dump(mode='json');normalized['nodes'].sort(key=lambda n:n['node_ref'])
    return seal({'mode':'offline-synthetic-communication-object','schema_version':obj.schema_version,'object':normalized,
                 'source_digests_independently_verified':False,'integrity_scope':'canonical fixture hashes and exact declared parent links; no external authenticity attestation',
                 'immutable_fixture_contract':True},tenant,'12.0.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-synthetic-communication-object','schema_version':'scec.communication-object/1'},str(tenant),'12.0.0')


@router.post('/preview')
def preview(payload:CommunicationObject,tenant=Depends(_scope)):
    try:return preview_object(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/commit')
@router.post('/publish')
@router.post('/send')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live communication object operations disabled')
