"""Evidence-derived synthetic channel bundles, without recipients or transport."""
import hashlib
import json
from datetime import timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, StrictBool, field_validator, model_validator
from .newsletter_alerts_v1130 import Fixture, SyntheticPreviewRoute, opaque, ResearchAlert, Topic
from .communication_objects_v1200 import CommunicationObject, EvidencePointer, preview_object
from .institutional_newsroom_v1120 import NewsroomEntry, NewsroomPreview, assess as newsroom_assess
from .research_distribution_v1100 import DistributionPreview, preview as distribution_preview
from .feed_serialization_v1110 import FeedEntry, FeedPreview, render as render_feed
from .citation_discovery_v1150 import text, public_url
from .offline_staging import scope, seal

router=APIRouter(prefix='/v1/campaign-composer',tags=['campaign-composer-staging'],route_class=SyntheticPreviewRoute)
_scope=scope('SCEC_CAMPAIGNS_STAGING_ENABLED')
BLOCKED_ACTIONS=('send','publish','subscribe','export-recipients','schedule','enqueue','activate','delete','federate')
Channel=Literal['newsroom','digest','research-alert','press-brief']


class StrictEntry(NewsroomEntry):
    summary: str = Field(min_length=1,max_length=500)
    kind: Literal['research-release','methodology-note','data-release']
    rights_reviewed: StrictBool=False
    editorial_reviewed: StrictBool=False
    source_integrity_reviewed: StrictBool=False
    privacy_reviewed: StrictBool=False
    institutional_approved: StrictBool=False

    @field_validator('headline','summary')
    @classmethod
    def safe_text(cls,v):return text(v)

    @field_validator('canonical_url')
    @classmethod
    def safe_url(cls,v):return public_url(v)


class StrictDistribution(DistributionPreview):
    editorial_reviewed: StrictBool=False
    privacy_reviewed: StrictBool=False
    source_integrity_reviewed: StrictBool=False
    distribution_approved: StrictBool=False


class Campaign(Fixture):
    campaign_ref: str = Field(min_length=3,max_length=96)
    revision: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,48}$')
    communication: CommunicationObject
    communication_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    announcement_evidence: EvidencePointer
    source_entry: StrictEntry
    source_distribution: StrictDistribution
    newsroom_title: str = Field(min_length=1,max_length=160)
    newsroom_url: str = Field(min_length=10,max_length=300)
    channels: tuple[Channel,...] = Field(min_length=1,max_length=4)
    topics: tuple[Topic,...] = Field(min_length=1,max_length=8)
    suppressed: StrictBool=False

    @field_validator('campaign_ref')
    @classmethod
    def reference(cls,v):return opaque(v)

    @field_validator('newsroom_title')
    @classmethod
    def label(cls,v):return text(v)

    @field_validator('newsroom_url')
    @classmethod
    def url(cls,v):return public_url(v)

    @field_validator('channels','topics')
    @classmethod
    def unique(cls,v):
        if len(v)!=len(set(v)):raise ValueError('Repeated selection')
        return tuple(sorted(v))

    @model_validator(mode='after')
    def lineage(self):
        if self.communication.organization_id!=self.organization_id or self.announcement_evidence.organization_id!=self.organization_id:raise ValueError('Cross-tenant campaign')
        if self.communication_sha256!=preview_object(self.communication,self.organization_id)['sha256']:raise ValueError('Stale communication hash')
        nodes={n.node_ref:n for n in self.communication.nodes}
        root=nodes[self.communication.root_node_ref];entry=self.source_entry;dist=self.source_distribution
        if self.announcement_evidence.node_ref not in nodes:raise ValueError('Missing announcement evidence')
        node=nodes[self.announcement_evidence.node_ref]
        if node.kind!='announcement' or node.evidence_sha256!=self.announcement_evidence.evidence_sha256:raise ValueError('Wrong or stale announcement pointer')
        permitted={'research-release':{'research-article','research-package','publication'},'methodology-note':{'methodology'},'data-release':{'dataset'}}
        if dist.object_kind not in permitted[entry.kind]:raise ValueError('Research object kind mismatch')
        if (dist.object_ref,dist.revision)!=(root.research_ref,root.research_revision) or (entry.announcement_ref,entry.revision)!=(dist.object_ref,dist.revision):raise ValueError('Research revision mismatch')
        if (node.artifact_ref,node.artifact_revision)!=(entry.announcement_ref,entry.revision):raise ValueError('Artifact revision mismatch')
        if sorted(entry.source_refs)!=sorted(dist.source_refs) or sorted(node.source_refs)!=sorted(entry.source_refs) or sorted(root.source_refs)!=sorted(entry.source_refs):raise ValueError('Source attribution mismatch')
        manifest=distribution_preview(dist,self.organization_id)
        assessment=newsroom_assess(NewsroomPreview(newsroom_title=self.newsroom_title,newsroom_url=self.newsroom_url,entries=[entry]),self.organization_id)
        if root.source_digest!=manifest['manifest_sha256'] or node.source_digest!=assessment['sha256']:raise ValueError('Source digest does not match regenerated preview')
        return self


def compose_campaign(campaign:Campaign,tenant:str):
    if campaign.organization_id!=tenant:raise ValueError('Tenant mismatch')
    entry=campaign.source_entry
    news=newsroom_assess(NewsroomPreview(newsroom_title=campaign.newsroom_title,newsroom_url=campaign.newsroom_url,entries=[entry]),tenant)
    distribution=distribution_preview(campaign.source_distribution,tenant)
    reviewed=news['entries'][0]['editorial_review_complete'] and entry.editorial_state=='approved-preview' and distribution['human_review_complete']
    eligible=reviewed and not campaign.suppressed
    variations=[]
    if eligible:
        for channel in campaign.channels:
            if channel=='newsroom':body={'headline':entry.headline,'summary':entry.summary,'canonical_url':entry.canonical_url}
            elif channel=='digest':
                # Existing serializer, not a new feed implementation or serving route.
                feed=render_feed(FeedPreview(format='json-feed',feed_title=campaign.newsroom_title,feed_description='Synthetic campaign digest preview',home_url=campaign.newsroom_url,feed_url=campaign.newsroom_url,entries=[FeedEntry(object_ref=entry.announcement_ref,revision=entry.revision,title=entry.headline,summary=entry.summary,canonical_url=entry.canonical_url,updated_at=entry.updated_at,source_refs=entry.source_refs,rights_reviewed=True,editorial_reviewed=True,privacy_reviewed=True,distribution_approved=True)]),tenant)
                body={'media_type':feed['media_type'],'content_preview':feed['content_preview'],'content_sha256':feed['sha256']}
            elif channel=='research-alert':
                alert=ResearchAlert(synthetic=True,organization_id=tenant,object_ref=entry.announcement_ref,revision=entry.revision,headline=entry.headline,summary=entry.summary,source_refs=entry.source_refs,topics=list(campaign.topics),review_state='approved-preview',privacy_reviewed=True,editorial_reviewed=True,source_integrity_reviewed=True,distribution_reviewed=True,rights_reviewed=True)
                body={'alert_contract':alert.model_dump(mode='json'),'recipient_selection_performed':False}
            else:body={'brief_type':'synthetic-press-brief','headline':entry.headline,'summary':entry.summary,'canonical_url':entry.canonical_url,'spokesperson_assigned':False,'embargo_clearance_granted':False}
            variations.append({'channel':channel,'research_ref':entry.announcement_ref,'research_revision':entry.revision,'source_refs':sorted(entry.source_refs),'body':body})
    normalized=campaign.model_dump(mode='json')
    normalized['communication']['nodes'].sort(key=lambda n:n['node_ref'])
    normalized['source_entry']['source_refs'].sort()
    normalized['source_distribution']['source_refs'].sort()
    normalized['source_distribution']['targets'].sort()
    normalized['source_entry']['updated_at']=entry.updated_at.astimezone(timezone.utc).isoformat()
    input_hash=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return seal({'input_sha256':input_hash,'distribution_review_gates':distribution['review_gates'],'mode':'offline-evidence-derived-campaign-bundle','campaign_ref':campaign.campaign_ref,'revision':campaign.revision,
                 'communication_sha256':campaign.communication_sha256,'announcement_sha256':news['sha256'],'source_manifest_sha256':distribution['manifest_sha256'],
                 'requested_channels':list(campaign.channels),'topics':list(campaign.topics),'suppressed':campaign.suppressed,
                 'review_complete_for_preview_only':reviewed,'eligible_for_bundle_only':eligible,'variations':variations,
                 'recipient_selection_performed':False,'recipient_collection_enabled':False,'campaign_dispatch_enabled':False,
                 'source_verification_scope':'regenerated supplied distribution/newsroom fixture digests; no external truth or rights attestation'},tenant,'12.2.0')


@router.get('/status')
def status(tenant=Depends(_scope)):
    return seal({'mode':'offline-evidence-derived-campaign-bundle','recipient_collection_enabled':False,'campaign_dispatch_enabled':False},str(tenant),'12.2.0')


@router.post('/preview')
def preview(payload:Campaign,tenant=Depends(_scope)):
    try:return compose_campaign(payload,str(tenant))
    except ValueError:raise HTTPException(422,'Fixture tenant mismatch') from None


@router.post('/send')
@router.post('/publish')
@router.post('/subscribe')
@router.post('/export-recipients')
@router.post('/schedule')
@router.post('/enqueue')
@router.post('/activate')
@router.post('/delete')
@router.post('/federate')
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503,'Live campaign operations disabled')
