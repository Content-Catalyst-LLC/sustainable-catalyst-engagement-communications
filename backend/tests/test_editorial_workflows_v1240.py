import time
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.identity import mint_token
from app.rights_suppression_v1230 import simulate_policy
from app.editorial_workflows_v1240 import make_decision, ReviewDecision, ReviewWorkflow, simulate_workflow, ROLES, BLOCKED_ACTIONS
from app.offline_staging import DISABLED
from app.newsletter_alerts_v1130 import DANGER_FLAGS, EXTRA_DANGER_FLAGS
ORG='00000000-0000-0000-0000-000000000001';OTHER='00000000-0000-0000-0000-000000000002'
KEY='synthetic-staging-fixture-key-never-production';SYNTH={'synthetic':True,'organization_id':ORG}

def ref(number):return 'synthetic:'+str(UUID(int=number))

def decision(policy,role='editorial',**changes):
    return make_decision(**{**dict(decision_ref='decision:'+role,reviewer_ref=ref(20+ROLES.index(role)),role=role,outcome='approve',subject_sha256=simulate_policy(policy,ORG)['sha256'],subject_revision=policy.revision,decided_at='2026-10-27T00:00:00Z',reason_code='approved-synthetic',**SYNTH),**changes})

@pytest.fixture
def workflow_factory(policy_factory):
    def build(**changes):
        policy=policy_factory()
        return ReviewWorkflow(**{**dict(workflow_ref='workflow:fixture',revision='r1',author_ref=ref(10),policy=policy,policy_sha256=simulate_policy(policy,ORG)['sha256'],as_of=policy.as_of,decisions=tuple(decision(policy,role) for role in ROLES),**SYNTH),**changes})
    return build

@pytest.fixture
def client(monkeypatch):
    for flag in (*DANGER_FLAGS,*EXTRA_DANGER_FLAGS):monkeypatch.setenv(flag,'0')
    monkeypatch.setenv('SCEC_WORKFLOWS_STAGING_ENABLED','1');monkeypatch.setenv('SCEC_IDENTITY_MODE','bound')
    monkeypatch.setenv('SCEC_IDENTITY_SIGNING_KEY',KEY);monkeypatch.setenv('SCEC_ALLOWED_ORGANIZATION_IDS',ORG)
    return TestClient(app)

def headers(org=ORG,roles=('administrator',)):
    return {'Authorization':'Bearer '+mint_token(subject='synthetic-workflow-review',organization_id=org,roles=list(roles),expires_at=int(time.time())+300,secret=KEY),'X-SCEC-Organization-ID':org}


def test_complete_distinct_reviews_never_authorize_live_delivery(workflow_factory):
    r=simulate_workflow(workflow_factory(),ORG)
    assert r['all_reviews_complete_for_simulation'] and r['workflow_state']=='review-complete-preview'
    assert len(r['eligible_variations'])==2 and all(x['review_valid_for_simulation_only'] for x in r['reviews'])
    assert all(r[k] is False for k in DISABLED) and len(r['live_acceptance_gates_pending'])==7
    for flag in ['reviewer_identities_verified','reviewer_roles_verified','live_approval_executed','delivery_authorized','roles_changed']:assert r[flag] is False


@pytest.mark.parametrize('role',ROLES)
def test_each_role_is_required(workflow_factory,role):
    p=workflow_factory();p=workflow_factory(decisions=tuple(d for d in p.decisions if d.role!=role))
    r=simulate_workflow(p,ORG)
    assert not r['all_reviews_complete_for_simulation'] and not r['eligible_variations']
    assert 'review-missing' in next(x for x in r['reviews'] if x['role']==role)['review_flags']


@pytest.mark.parametrize('role',ROLES)
def test_author_cannot_self_approve(workflow_factory,role):
    p=workflow_factory();p=workflow_factory(author_ref=next(d for d in p.decisions if d.role==role).reviewer_ref)
    r=simulate_workflow(p,ORG);assert not r['all_reviews_complete_for_simulation']
    assert 'self-approval-denied' in next(x for x in r['reviews'] if x['role']==role)['review_flags']


def test_one_reviewer_cannot_fill_multiple_roles(workflow_factory):
    p=workflow_factory();records=[decision(p.policy,role,reviewer_ref=ref(99)) for role in ROLES]
    r=simulate_workflow(workflow_factory(decisions=tuple(records)),ORG)
    assert not r['eligible_variations'] and all('reviewer-role-collision' in x['review_flags'] for x in r['reviews'])


@pytest.mark.parametrize('outcome',['reject','abstain'])
def test_nonapproval_is_never_complete(workflow_factory,outcome):
    p=workflow_factory();records=list(p.decisions);records[0]=decision(p.policy,outcome=outcome,reason_code='needs-revision')
    r=simulate_workflow(workflow_factory(decisions=tuple(records)),ORG)
    assert not r['all_reviews_complete_for_simulation'] and 'approval-not-recorded' in r['reviews'][0]['review_flags']


def test_stale_subject_invalidates_prior_approvals(workflow_factory,policy_factory):
    p=workflow_factory();new=policy_factory(revision='r2')
    current=workflow_factory(policy=new,policy_sha256=simulate_policy(new,ORG)['sha256'],decisions=p.decisions)
    r=simulate_workflow(current,ORG)
    assert not r['eligible_variations'] and all('stale-subject-invalidated' in x['review_flags'] for x in r['reviews'])


@pytest.mark.parametrize('moment,reason',[('2026-10-28T00:00:00Z','decision-in-future'),('2026-10-26T00:00:00Z','decision-before-source-revision')])
def test_decision_clock_bounds(workflow_factory,moment,reason):
    p=workflow_factory();records=list(p.decisions);records[0]=decision(p.policy,decided_at=moment)
    r=simulate_workflow(workflow_factory(decisions=tuple(records)),ORG)
    assert not r['eligible_variations'] and reason in r['reviews'][0]['review_flags']
    with pytest.raises(ValidationError):workflow_factory(as_of='2026-10-28T00:00:00Z')


def test_hash_tampering_frozen_records_and_invalid_reason(workflow_factory):
    p=workflow_factory();record=p.decisions[0];data=record.model_dump();data['reviewer_ref']=ref(100)
    with pytest.raises(ValidationError):ReviewDecision(**data)
    with pytest.raises(ValidationError):record.outcome='reject'
    with pytest.raises(ValidationError):decision(p.policy,outcome='approve',reason_code='needs-revision')
    with pytest.raises(ValidationError):decision(p.policy,email='private@example.org')
    with pytest.raises(ValidationError):decision(p.policy,reviewer_ref='private@example.org')


def test_tenant_duplicates_stale_envelope_and_default_missing_reviews(workflow_factory):
    p=workflow_factory()
    with pytest.raises(ValidationError):workflow_factory(policy_sha256='a'*64)
    with pytest.raises(ValidationError):workflow_factory(decisions=(p.decisions[0],p.decisions[0]))
    with pytest.raises(ValidationError):workflow_factory(decisions=(decision(p.policy,organization_id=OTHER),))
    with pytest.raises(ValueError):simulate_workflow(p,OTHER)
    assert not simulate_workflow(workflow_factory(decisions=()),ORG)['eligible_variations']


def test_approval_does_not_override_source_policy(workflow_factory,policy_factory):
    policy=policy_factory(suppressed=True)
    p=workflow_factory(policy=policy,policy_sha256=simulate_policy(policy,ORG)['sha256'],decisions=tuple(decision(policy,r) for r in ROLES))
    r=simulate_workflow(p,ORG)
    assert all(x['review_valid_for_simulation_only'] for x in r['reviews'])
    assert not r['source_policy_eligible_for_preview'] and not r['all_reviews_complete_for_simulation'] and not r['eligible_variations']


def test_canonical_record_order_and_workflow_revision(workflow_factory):
    p=workflow_factory();r=simulate_workflow(p,ORG)
    assert r==simulate_workflow(workflow_factory(decisions=tuple(reversed(p.decisions))),ORG)
    assert r['sha256']!=simulate_workflow(workflow_factory(revision='r2'),ORG)['sha256']


def test_http_scope_and_validation_redaction(client,workflow_factory,monkeypatch):
    url='/v1/editorial-workflows/status';assert client.get(url).status_code==401
    assert client.get(url,headers=headers()).status_code==200
    assert client.get(url,headers=headers(OTHER)).status_code==403
    assert client.get(url,headers=headers(roles=('viewer',))).status_code==403
    data=workflow_factory().model_dump(mode='json');assert client.post('/v1/editorial-workflows/preview',headers=headers(),json=data).status_code==200
    data['email']='private@example.org';r=client.post('/v1/editorial-workflows/preview',headers=headers(),json=data);assert r.status_code==422 and 'private@example.org' not in r.text
    monkeypatch.setenv('SCEC_WORKFLOWS_STAGING_ENABLED','0');assert client.get(url,headers=headers()).status_code==503


@pytest.mark.parametrize('action',BLOCKED_ACTIONS)
def test_no_live_approval_role_change_or_dispatch(client,action):
    assert client.post('/v1/editorial-workflows/'+action,headers=headers()).status_code==503


@pytest.mark.parametrize('flag',(*DANGER_FLAGS,*EXTRA_DANGER_FLAGS))
def test_danger_flags_deny(client,monkeypatch,flag):
    monkeypatch.setenv(flag,'1');assert client.get('/v1/editorial-workflows/status',headers=headers()).status_code==503
