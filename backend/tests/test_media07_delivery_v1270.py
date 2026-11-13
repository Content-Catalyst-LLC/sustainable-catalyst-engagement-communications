"""MEDIA-07: Substack-first offline plan, optional premium provider is disabled."""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.media07_delivery_v1270 import NewsletterPlan, blocked, plan, status

TENANT = "00000000-0000-4000-8000-000000000001"

def example(**overrides):
    data = dict(
        title="Research Bulletin", subject="Evidence and Policy",
        preheader="Sustainable Catalyst research news",
        approved_revision_sha256="a"*64,
        channels=["substack_manual", "premium_provider_future"],
    )
    return NewsletterPlan(**(data | overrides))

def test_primary_channel_is_substack_and_no_delivery():
    out = status(tenant=TENANT)
    assert out["release"] == "MEDIA-07"
    assert out["primary_distribution"] == "substack_manual"
    assert out["premium_delivery_adapter_enabled"] is False
    assert out["campaign_send_enabled"] is False
    assert out["production_certified"] is False

def test_plan_deterministic_and_no_provider_calls():
    req=example()
    one=plan(req, tenant=TENANT)
    two=plan(req, tenant=TENANT)
    assert one["input_sha256"]==two["input_sha256"]
    assert one["recipient_selection_performed"] is False
    assert one["provider_api_request_performed"] is False
    assert [x["action"] for x in one["channels"]] == [
        "substack_compatible_export","future_provider_not_configured"
    ]
    assert all(x["status"]=="not_executed" for x in one["channels"])

@pytest.mark.parametrize("bad", [
    {"channels":["substack_manual","substack_manual"]},
    {"channels":[]},
    {"approved_revision_sha256":"0"},
    {"channels":["substack_automatic"]},
    {"channels":["self_hosted_email"]},
    {"recipient_email":"someone@example.com"},
])
def test_unapproved_inputs_fail_closed(bad):
    with pytest.raises(ValidationError):
        example(**bad)

def test_dispatch_stays_blocked():
    with pytest.raises(HTTPException) as exc:
        blocked(tenant=TENANT)
    assert exc.value.status_code==503
