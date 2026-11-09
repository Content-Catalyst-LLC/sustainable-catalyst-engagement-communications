"""MEDIA-07: offline integration contract. Never touches SMTP, listmonk, or user data."""
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
        channels=["self_hosted_email","substack_manual"],
    )
    return NewsletterPlan(**(data | overrides))

def test_status_denies_all_live_delivery():
    out = status(tenant=TENANT)
    assert out["release"] == "MEDIA-07"
    assert out["campaign_send_enabled"] is False
    assert out["listmonk_api_access_enabled"] is False
    assert out["production_certified"] is False

def test_offline_plan_is_deterministic_and_never_dispatches():
    req=example()
    one=plan(req,tenant=TENANT)
    two=plan(req,tenant=TENANT)
    assert one["input_sha256"]==two["input_sha256"]
    assert one["recipient_selection_performed"] is False
    assert one["listmonk_api_request_performed"] is False
    assert [x["action"] for x in one["channels"]] == ["listmonk_draft_only","substack_manual_export"]
    assert all(x["status"]=="not_executed" for x in one["channels"])

@pytest.mark.parametrize("bad", [
    {"channels":["self_hosted_email","self_hosted_email"]},
    {"channels":[]},
    {"approved_revision_sha256":"0"},
    {"channels":["substack_automatic"]},
    {"recipient_email":"someone@example.com"},
])
def test_disallowed_inputs_fail_closed(bad):
    with pytest.raises(ValidationError):
        example(**bad)

def test_dispatch_is_blocked():
    with pytest.raises(HTTPException) as exc:
        blocked(tenant=TENANT)
    assert exc.value.status_code==503
