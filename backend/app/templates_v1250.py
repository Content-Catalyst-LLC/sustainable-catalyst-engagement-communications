"""Private, evidence-derived structured template previews; no public renderer."""
import hashlib
import html
import json
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute
from .communication_objects_v1200 import EvidencePointer
from .editorial_workflows_v1240 import ReviewWorkflow, simulate_workflow
from .events_v1160 import Event, preview_event
from .citation_discovery_v1150 import Publication, export as citation_export
from .offline_staging import scope, seal
from .embeds_v1180 import API_HEADERS

router=APIRouter(prefix='/v1/institutional-templates',tags=['institutional-templates-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_TEMPLATES_STAGING_ENABLED')
TEMPLATES=('newsroom','digest','research-alert','press-brief','webinar-notice','publication-summary')
LABELS={'newsroom':'Research update','digest':'Research digest','research-alert':'Research alert','press-brief':'Press brief','webinar-notice':'Webinar notice','publication-summary':'Publication summary'}
BLOCKED_ACTIONS=('publish','serve-public','send','install-template','activate','delete','federate')


class TemplateRequest(Fixture):
    template: Literal['newsroom','digest','research-alert','press-brief','webinar-notice','publication-summary']
    workflow: ReviewWorkflow
    workflow_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    additional_evidence: EvidencePointer | None = None
    event: Event | None = None
    publication: Publication | None = None

    @model_validator(mode='after')
    def integrity(self):
        if self.workflow.organization_id!=self.organization_id:raise ValueError('Cross-tenant template')
        if self.workflow_sha256!=simulate_workflow(self.workflow,self.organization_id)['sha256']:raise ValueError('Stale review workflow')
        if self.event is not None and self.template!='webinar-notice':raise ValueError('Unused event facts')
        if self.publication is not None and self.template!='publication-summary':raise ValueError('Unused publication facts')
        payload=self.event if self.template=='webinar-notice' else self.publication if self.template=='publication-summary' else None
        if payload is None:
            if self.additional_evidence is not None:raise ValueError('Evidence pointer without facts')
            return self
        if payload.organization_id!=self.organization_id or self.additional_evidence is None or self.additional_evidence.organization_id!=self.organization_id:raise ValueError('Missing or cross-tenant evidence')
        nodes={n.node_ref:n for n in self.workflow.policy.campaign.communication.nodes}
        ptr=self.additional_evidence
        if ptr.node_ref not in nodes or nodes[ptr.node_ref].evidence_sha256!=ptr.evidence_sha256:raise ValueError('Stale source pointer')
        node=nodes[ptr.node_ref]
        if self.event is not None:
            if self.event.kind!='webinar':raise ValueError('Webinar template requires webinar facts')
            result=preview_event(self.event,self.organization_id);kind='event';ref=self.event.event_ref;revision='seq:'+str(self.event.revision)
        else:
            result=citation_export(self.publication,self.organization_id);kind='citation';ref=self.publication.object_ref;revision=self.publication.revision
        if node.kind!=kind or (node.artifact_ref,node.artifact_revision)!=(ref,revision):raise ValueError('Source kind or revision mismatch')
        if node.source_digest!=result['sha256'] or sorted(node.source_refs)!=sorted(payload.source_refs):raise ValueError('Regenerated source evidence mismatch')
        return self


def render_template(request:TemplateRequest,tenant:str):
    if request.organization_id!=tenant:raise ValueError('Tenant mismatch')
    workflow=simulate_workflow(request.workflow,tenant);entry=request.workflow.policy.campaign.source_entry
    reasons=[]
    if not workflow['all_reviews_complete_for_simulation']:reasons.append('workflow-review-incomplete')
    if request.template=='webinar-notice':
        if request.event is None:reasons.append('event-evidence-missing')
        elif preview_event(request.event,tenant)['ics_preview'] is None:reasons.append('event-preview-ineligible')
    if request.template=='publication-summary' and request.publication is None:reasons.append('publication-evidence-missing')
    document=None;markup=None
    if not reasons:
        title=entry.headline;sections=[{'level':2,'heading':'Research summary','paragraphs':[entry.summary]}]
        links=[{'label':'Read the canonical research source','url':entry.canonical_url}]
        if request.event is not None:
            e=request.event;title=e.title
            sections.append({'level':2,'heading':'Event schedule and status','paragraphs':[e.starts_at.isoformat()+' to '+e.ends_at.isoformat()+' ('+e.timezone_name+')','Status: '+e.lifecycle,'Speakers: '+'; '.join(s.attribution for s in e.speakers)]})
            if e.change_notice:sections.append({'level':2,'heading':'Event update','paragraphs':[e.change_notice]})
            links.append({'label':'Read the canonical event notice','url':e.canonical_url})
        if request.publication is not None:
            p=request.publication;title=p.title
            sections.append({'level':2,'heading':'Publication metadata','paragraphs':['Authors: '+'; '.join(a.name for a in p.authors),'Year: '+str(p.year),*(['Supplied DOI: '+p.doi] if p.doi else ['No DOI supplied'])]})
            for relation in p.relations:
                sections.append({'level':2,'heading':relation.kind.capitalize()+' notice','paragraphs':['Explicit source-linked publication notice; no independent verification.']})
                links.append({'label':'Read the '+relation.kind+' notice','url':relation.url})
            links.append({'label':'Read the canonical publication record','url':p.canonical_url})
        document={'schema_version':'scec.institutional-template/1','brand':'Sustainable Catalyst','template':request.template,'template_label':LABELS[request.template],'language':'en','heading':{'level':1,'text':title},'sections':sections,'links':links,'images':[],
                  'source_refs':sorted(set(entry.source_refs)|set(request.event.source_refs if request.event else request.publication.source_refs if request.publication else [])),
                  'notice':'Synthetic private authoring preview. Unpublished; no delivery authorization.'}
        markup='<article lang="en" aria-label="'+html.escape(LABELS[request.template],quote=True)+'"><header><p>Sustainable Catalyst</p><p>'+html.escape(LABELS[request.template])+'</p><h1>'+html.escape(title)+'</h1></header>'
        for section in sections:
            markup+='<section><h2>'+html.escape(section['heading'])+'</h2>'+''.join('<p>'+html.escape(p)+'</p>' for p in section['paragraphs'])+'</section>'
        markup+='<nav aria-label="Research source references"><ul>'+''.join('<li><a rel="noreferrer noopener" href="'+html.escape(link['url'],quote=True)+'">'+html.escape(link['label'])+'</a></li>' for link in links)+'</ul></nav><footer><p>'+html.escape(document['notice'])+'</p></footer></article>'
    normalized=request.model_dump(mode='json',exclude={'workflow'})
    input_hash=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return seal({'mode':'private-synthetic-institutional-template','template':request.template,'workflow_sha256':request.workflow_sha256,'input_sha256':input_hash,
                 'withheld_reasons':reasons,'document':document,'html_fragment_preview':markup,
                 'source_policy_channels':[v['channel'] for v in workflow['eligible_variations']],
                 'template_authoring_only':True,'channel_distribution_approval_granted':False,'delivery_authorized':False,
                 'public_renderer_enabled':False,'remote_resources_enabled':False,'wcag_conformance_certified':False,
                 'required_future_html_headers':{'Content-Security-Policy':"default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; sandbox",'Cache-Control':'no-store, private','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'}},tenant,'12.5.0')


@router.get('/status')
def status(response:Response,tenant=Depends(_scope)):
    response.headers.update(API_HEADERS)
    return seal({'mode':'private-synthetic-institutional-template','supported_templates':list(TEMPLATES),'public_renderer_enabled':False,'delivery_authorized':False},str(tenant),'12.5.0')


@router.post('/preview')
def preview(payload:TemplateRequest,response:Response,tenant=Depends(_scope)):
    response.headers.update(API_HEADERS)
    try:return render_template(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/publish')
@router.post('/serve-public')
@router.post('/send')
@router.post('/install-template')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live template operations disabled')
