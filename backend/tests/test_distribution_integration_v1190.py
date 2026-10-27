"""Cross-release fixture adapters exercise actual functions, without a new orchestrator."""
from datetime import datetime, timezone
from uuid import UUID
import socket
import pytest
from app.research_distribution_v1100 import DistributionPreview, preview
from app.feed_serialization_v1110 import FeedEntry, FeedPreview, render
from app.institutional_newsroom_v1120 import NewsroomEntry, NewsroomPreview, assess as newsroom
from app.newsletter_alerts_v1130 import ResearchAlert, SubscriptionPreference, AlertPreview, compose
from app.media_relations_v1140 import PressPackage, OutletClassification, assess as press
from app.citation_discovery_v1150 import Publication, Author, export
from app.events_v1160 import Event, Speaker, preview_event
from app.partnerships_v1170 import Artifact, Partner, PartnerPackage, plan
from app.embeds_v1180 import Embed, render_embed
from app.audience_v1190 import AudienceEvent, MetricSource, AudienceBatch, aggregate_audience

ORG='00000000-0000-0000-0000-000000000001'
REF='research:integration';SOURCE='source:integration';REV='r1'
NOW=datetime(2026,10,27,tzinfo=timezone.utc)
SYNTH={'synthetic':True,'organization_id':ORG}
META={'source_refs':[SOURCE],'revision':REV}
TEXT={'canonical_url':'https://example.org/research','summary':'Synthetic integration summary'}


def pipeline(reviewed):
    foundation=preview(DistributionPreview(object_ref=REF,object_kind='publication',targets=['institutional-newsroom'],rights_basis='open-license',editorial_reviewed=reviewed,privacy_reviewed=reviewed,source_integrity_reviewed=reviewed,distribution_approved=reviewed,**META),ORG)
    feed=render(FeedPreview(format='json-feed',feed_title='Synthetic feed',feed_description='Synthetic fixture',home_url=TEXT['canonical_url'],feed_url='https://example.org/feed',entries=[FeedEntry(object_ref=REF,title='Synthetic title',updated_at=NOW,rights_reviewed=reviewed,editorial_reviewed=reviewed,privacy_reviewed=reviewed,distribution_approved=reviewed,**TEXT,**META)]),ORG)
    news=newsroom(NewsroomPreview(newsroom_title='Synthetic newsroom',newsroom_url='https://example.org/news',entries=[NewsroomEntry(announcement_ref=REF,kind='research-release',editorial_state='approved-preview',headline='Synthetic title',updated_at=NOW,rights_reviewed=reviewed,editorial_reviewed=reviewed,source_integrity_reviewed=reviewed,privacy_reviewed=reviewed,institutional_approved=reviewed,**TEXT,**META)]),ORG)
    alert=compose(AlertPreview(alert=ResearchAlert(object_ref=REF,headline='Synthetic title',summary=TEXT['summary'],topics=['methods-data'],review_state='approved-preview',privacy_reviewed=reviewed,editorial_reviewed=reviewed,source_integrity_reviewed=reviewed,distribution_reviewed=reviewed,rights_reviewed=reviewed,**SYNTH,**META),preferences=[SubscriptionPreference(subscriber_ref='synthetic:'+str(UUID(int=11)),topics=['methods-data'],channels=['email'],consent=reviewed,state='active-preview',**SYNTH)]),ORG)
    media=press(PressPackage(package_ref=REF,headline='Synthetic title',pitch='Synthetic pitch',spokesperson_ref='synthetic:'+str(UUID(int=12)),as_of=NOW,outlets=[OutletClassification(outlet_ref='synthetic:'+str(UUID(int=13)),kind='academic',topics=['methods'],**SYNTH)],review_state='approved-preview',rights_reviewed=reviewed,sources_verified=reviewed,spokesperson_verified=reviewed,institutional_approved=reviewed,editorial_reviewed=reviewed,privacy_reviewed=reviewed,**SYNTH,**META),ORG)
    citation=export(Publication(object_ref=REF,title='Synthetic title',authors=[Author(name='Synthetic Author',**SYNTH)],year=2026,canonical_url=TEXT['canonical_url'],**SYNTH,**META),ORG)
    event=preview_event(Event(event_ref=REF,revision=0,kind='webinar',title='Synthetic webinar',description='Synthetic discussion',canonical_url=TEXT['canonical_url'],starts_at='2026-11-01T12:00:00Z',ends_at='2026-11-01T13:00:00Z',updated_at=NOW,timezone_name='UTC',lifecycle='scheduled',source_refs=[SOURCE],speakers=[Speaker(speaker_ref='synthetic:'+str(UUID(int=14)),attribution='Synthetic Speaker',privacy_reviewed=reviewed,attribution_reviewed=reviewed,**SYNTH)],editorial_reviewed=reviewed,rights_reviewed=reviewed,privacy_reviewed=reviewed,**SYNTH),ORG)
    partners=plan(PartnerPackage(package_ref=REF,revision=REV,institution_ref='institution:owner',artifacts=[Artifact(object_ref=REF,object_kind='publication',license='cc-by',classification='public',rights_reviewed=reviewed,editorial_reviewed=reviewed,privacy_reviewed=reviewed,source_integrity_reviewed=reviewed,distribution_reviewed=reviewed,**SYNTH,**META)],partners=[Partner(partner_ref='partner:synthetic',institution_ref='institution:other',kind='research',accepted_licenses=['cc-by'],allowed_classifications=['public'],institutional_reviewed=reviewed,rights_reviewed=reviewed,**SYNTH)],**SYNTH),ORG)
    embed=render_embed(Embed(object_ref=REF,title='Synthetic title',requested_origin='https://example.org',updated_at=NOW,expires_at='2026-10-28T00:00:00Z',as_of=NOW,rights_reviewed=reviewed,editorial_reviewed=reviewed,privacy_reviewed=reviewed,distribution_reviewed=reviewed,**SYNTH,**TEXT,**META),ORG,['https://example.org'])
    metrics=aggregate_audience(AudienceBatch(events=[AudienceEvent(event_ref='synthetic:'+str(UUID(int=20+i)),reader_ref='synthetic:'+str(UUID(int=30+i)),object_ref=REF,revision=REV,channel='embed',kind='view',occurred_day='2026-10-27',source_ref=SOURCE,**SYNTH) for i in range(5)],sources=[MetricSource(source_ref=SOURCE,edition='integration-r1',**SYNTH)],**SYNTH),ORG)
    return [foundation,feed,news,alert,media,citation,event,partners,embed,metrics]


@pytest.mark.parametrize('reviewed',[False,True])
def test_full_v11_chain_preserves_lineage_and_disabled_operations(monkeypatch,reviewed):
    def no_network(*a,**k):raise AssertionError('Offline integration attempted network transport')
    monkeypatch.setattr(socket.socket,'connect',no_network)
    monkeypatch.setattr(socket,'create_connection',no_network)
    results=pipeline(reviewed)
    assert [r['release'] for r in results]==['11.'+str(i)+'.0' for i in range(10)]
    for index,result in enumerate(results):
        assert result['organization_id']==ORG
        if index==0:
            assert result['review_gates']['production_acceptance'] is False
            assert result['requires_live_production_acceptance'] is True
        else:
            assert result['production_certified'] is False
        assert result['persisted'] is False and result['live_acceptance_gates_pending']==results[0]['live_acceptance_gates_pending']
        assert len(result['live_acceptance_gates_pending'])==7
        for flag in ['publication_authorized','actual_publication_enabled','outbound_communications_enabled','federation_enabled','production_writes_enabled']:
            if flag in result:assert result[flag] is False
    assert results[0]['object_ref']==REF
    assert results[2]['entries'][0]['announcement_ref']==REF and results[2]['entries'][0]['source_refs']==[SOURCE]
    assert results[3]['alert']['object_ref']==REF and results[5]['fixture']['object_ref']==REF
    assert results[7]['distribution_manifests'][0]['source_manifest']['manifest_sha256']==results[0]['manifest_sha256']
    assert results[8]['object_ref']==REF and results[9]['provenance'][0]['source_ref']==SOURCE
    assert results[3]['preview_eligible_count']==int(reviewed)
    assert (results[4]['pitch_preview'] is not None)==reviewed
    assert (results[6]['ics_preview'] is not None)==reviewed
    assert results[7]['routing_decisions'][0]['eligible_for_synthetic_plan_only']==reviewed
    assert (results[8]['content'] is not None)==reviewed
    assert results==pipeline(reviewed)
