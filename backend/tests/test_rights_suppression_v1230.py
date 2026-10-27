import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.campaigns_v1220 import compose_campaign
from app.rights_suppression_v1230 import PurposeRule, RightsRule, RetentionRule, PolicySimulation, simulate_policy, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production';SYNTH={'synthetic':True,'organization_id':ORG}

def purpose(**changes):
    return PurposeRule(**{**dict(purpose='research-alert',consent_state='granted',consent_reviewed=True,evidence_ref='consent:fixture',allowed_channels=('digest','research-alert'),valid_from='2026-10-26T00:00:00Z',valid_until='2026-10-28T00:00:00Z',**SYNTH),**changes})

def rights(**changes):
    return RightsRule(**{**dict(source_ref='source:fixture',policy_revision='r1',license='cc-by',rights_reviewed=True,attribution_reviewed=True,**SYNTH),**changes})

def retention(**changes):
    return RetentionRule(**{**dict(recorded_day='2026-10-01',retention_days=90,privacy_reviewed=True,**SYNTH),**changes})

@pytest.fixture
def policy_factory(campaign_factory):
    def build(**changes):
        campaign=campaign_factory(channels=('digest','research-alert'))
        return PolicySimulation(**{**dict(policy_ref='policy:fixture',revision='r1',campaign=campaign,campaign_sha256=compose_campaign(campaign,ORG)['sha256'],as_of='2026-10-27T00:00:00Z',purpose_rule=purpose(),rights=(rights(),),retention=retention(),classification='public',embargo_reviewed=True,**SYNTH),**changes})
    return build

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_POLICY_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-policy-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_reviewed_policy_is_only_a_synthetic_simulation(policy_factory):
    r=simulate_policy(policy_factory(),ORG)
    assert len(r['eligible_variations'])==2 and all(d['eligible_for_synthetic_policy_preview_only'] for d in r['channel_decisions'])
    assert all(r[k] is False for k in DISABLED)
    for key in ['consent_verified','consent_changed','erasure_authorized','actual_records_deleted','policy_authorizes_delivery','legal_determination']:assert r[key] is False
    assert r['governance_preview']['consent_verified'] is False and r['governance_preview']['erasure_authorized'] is False
    assert len(r['live_acceptance_gates_pending'])==7


@pytest.mark.parametrize('changes,reason',[({'consent_state':'withdrawn'},'synthetic-consent-not-granted'),({'consent_state':'denied'},'synthetic-consent-not-granted'),({'consent_state':'not-recorded'},'synthetic-consent-not-granted'),({'consent_reviewed':False},'consent-evidence-review-required'),({'evidence_ref':None},'consent-evidence-review-required'),({'valid_until':None},'consent-validity-missing'),({'valid_until':'2026-10-27T00:00:00Z'},'consent-outside-validity'),({'valid_from':'2026-10-27T00:00:01Z'},'consent-outside-validity')])
def test_missing_withdrawn_or_expired_consent_denies(policy_factory,changes,reason):
    r=simulate_policy(policy_factory(purpose_rule=purpose(**changes)),ORG)
    assert not r['eligible_variations'] and all(reason in d['review_flags'] for d in r['channel_decisions'])


@pytest.mark.parametrize('changes,reason',[({'retention_days':None},'retention-insufficient-metadata'),({'recorded_day':None},'retention-insufficient-metadata'),({'recorded_day':'2026-10-28'},'future-collection-date'),({'retention_days':1},'retention-review-due'),({'privacy_reviewed':False},'privacy-retention-review-required'),({'deletion_hold':True},'hold-review')])
def test_retention_metadata_never_deletes_records(policy_factory,changes,reason):
    r=simulate_policy(policy_factory(retention=retention(**changes)),ORG)
    assert not r['eligible_variations'] and all(reason in d['review_flags'] for d in r['channel_decisions'])
    assert not r['actual_records_deleted'] and not r['erasure_authorized']


@pytest.mark.parametrize('changes,reason',[({'license':'unknown'},'license-not-permitted'),({'license':'restricted'},'license-not-permitted'),({'rights_reviewed':False},'source-rights-review-required'),({'attribution_reviewed':False},'source-rights-review-required'),({'license':'author-owned'},'source-permission-required'),({'license':'permission-required'},'source-permission-required')])
def test_licence_or_permission_unknown_denies(policy_factory,changes,reason):
    r=simulate_policy(policy_factory(rights=(rights(**changes),)),ORG)
    assert not r['eligible_variations'] and all(reason in d['review_flags'] for d in r['channel_decisions'])


def test_permission_fixture_and_missing_rights(policy_factory):
    assert simulate_policy(policy_factory(rights=(rights(license='permission-required',permission_documented=True),)),ORG)['eligible_variations']
    assert not simulate_policy(policy_factory(rights=()),ORG)['eligible_variations']


@pytest.mark.parametrize('changes,reason',[({'embargo_reviewed':False},'embargo-review-required'),({'embargo_until':'2026-10-27T00:00:01Z'},'embargo-active'),({'suppressed':True},'suppressed'),({'classification':'internal'},'nonpublic-content-denied'),({'classification':'restricted'},'nonpublic-content-denied')])
def test_embargo_access_and_suppression(policy_factory,changes,reason):
    r=simulate_policy(policy_factory(**changes),ORG)
    assert not r['eligible_variations'] and all(reason in d['review_flags'] for d in r['channel_decisions'])


def test_purpose_and_channel_limits(policy_factory):
    r=simulate_policy(policy_factory(purpose_rule=purpose(allowed_channels=('digest',))),ORG)
    assert [v['channel'] for v in r['eligible_variations']]==['digest']
    r=simulate_policy(policy_factory(purpose_rule=purpose(purpose='press-information')),ORG)
    assert not r['eligible_variations'] and all('purpose-channel-mismatch' in d['review_flags'] for d in r['channel_decisions'])


def test_metadata_strictness_duplicates_stale_and_tenants(policy_factory):
    with pytest.raises(ValidationError):purpose(consent_reviewed='yes')
    with pytest.raises(ValidationError):retention(retention_days=True)
    with pytest.raises(ValidationError):rights(permission_documented=1)
    with pytest.raises(ValidationError):policy_factory(rights=(rights(),rights()))
    with pytest.raises(ValidationError):policy_factory(rights=(rights(source_ref='source:missing'),))
    with pytest.raises(ValidationError):policy_factory(purpose_rule=purpose(organization_id=OTHER))
    with pytest.raises(ValidationError):policy_factory(campaign_sha256='a'*64)
    with pytest.raises(ValidationError):purpose(valid_from='2026-10-27T00:00:00')
    with pytest.raises(ValueError):simulate_policy(policy_factory(),OTHER)


def test_policy_hash_changes_with_rule_revision_and_purpose(policy_factory):
    first=simulate_policy(policy_factory(),ORG)['sha256']
    assert first!=simulate_policy(policy_factory(rights=(rights(policy_revision='r2'),)),ORG)['sha256']
    assert first!=simulate_policy(policy_factory(purpose_rule=purpose(purpose='institutional-update')),ORG)['sha256']


def test_http_scope_and_private_errors(client,policy_factory,monkeypatch):
    url='/v1/communications-policy/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=policy_factory().model_dump(mode='json');assert client.post('/v1/communications-policy/preview',headers=headers(),json=data).status_code==200
    data['subscriber_email']='private@example.org';r=client.post('/v1/communications-policy/preview',headers=headers(),json=data);assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_POLICY_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_consent_mutation_or_delivery(client,action):
    assert client.post('/v1/communications-policy/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/communications-policy/status',headers=headers()).status_code==503


def test_ineligible_source_cannot_be_overridden(policy_factory,campaign_factory):
    campaign=campaign_factory(suppressed=True)
    policy=policy_factory(campaign=campaign,campaign_sha256=compose_campaign(campaign,ORG)['sha256'])
    r=simulate_policy(policy,ORG)
    assert not r['eligible_variations'] and all('source-bundle-ineligible' in d['review_flags'] for d in r['channel_decisions'])


def test_dst_validity_uses_utc_and_default_policy_denies(policy_factory):
    policy=policy_factory(as_of='2026-11-01T01:45:00-05:00',purpose_rule=purpose(valid_from='2026-11-01T01:30:00-05:00',valid_until='2026-11-01T01:30:00-06:00'))
    assert simulate_policy(policy,ORG)['eligible_variations']
    minimal=policy_factory(purpose_rule=PurposeRule(purpose='research-alert',**SYNTH),rights=(),retention=RetentionRule(**SYNTH),embargo_reviewed=False,classification='restricted')
    assert not simulate_policy(minimal,ORG)['eligible_variations']
