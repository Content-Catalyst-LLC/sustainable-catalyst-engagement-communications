"""MEDIA-09.1 isolated HTTP and domain tests; no PostgreSQL or actual contacts."""
from uuid import UUID, uuid4
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.identity import mint_token
from app import media09_press as press
from app.persistence.media09 import press_inquiry_details

SECRET = "synthetic-media09-press-secret-key-local-123456789"
CLIENT = TestClient(app)


def setup(monkeypatch, role="contact_editor", tenant=None):
    tenant = tenant or uuid4()
    for k, v in {
        "SCEC_MEDIA09_PRESS_STAGING_ENABLED": "1",
        "SCEC_IDENTITY_MODE": "bound",
        "SCEC_IDENTITY_SIGNING_KEY": SECRET,
        "SCEC_ALLOWED_ORGANIZATION_IDS": str(tenant),
        "SCEC_PERSISTENCE_ENABLED": "1",
        "SCEC_DATABASE_URL": "postgresql+psycopg://fixture:fixture@127.0.0.1/scec_engagement_media09_test",
        "SCEC_ENV": "development",
    }.items():
        monkeypatch.setenv(k, v)
    token = mint_token(subject="synthetic-reviewer", organization_id=tenant,
                       roles={role}, expires_at=int(time.time()) + 300, secret=SECRET)
    return tenant, {"Authorization": "Bearer " + token, "X-SCEC-Organization-ID": str(tenant)}


def item(**kw):
    return dict(
        synthetic=True, idempotency_key=str(uuid4()), name="Synthetic Press Person",
        email="press@example.org", subject="Inquiry about climate evidence",
        message="Please share the public methods summary for review.",
        kind="press", privacy_notice_version=press.NOTICE,
        consent_to_reply=True, company="",
    ) | kw


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def fake_db():
    yield object()


def test_reviewer_status_and_form_spec(monkeypatch):
    _, headers = setup(monkeypatch)
    s = CLIENT.get("/v1/media09/press/status", headers=headers)
    assert s.status_code == 200, s.text
    assert s.json()["staging"] is True
    assert s.json()["public_intake_enabled"] is False
    assert s.json()["hubspot_connected"] is False
    f = CLIENT.get("/v1/media09/press/form-spec", headers=headers)
    assert f.status_code == 200 and f.json()["public_submission_url"] is None
    assert f.json()["privacy_notice_version"] == press.NOTICE


def test_off_by_default(monkeypatch):
    _, headers = setup(monkeypatch)
    monkeypatch.delenv("SCEC_MEDIA09_PRESS_STAGING_ENABLED")
    assert CLIENT.get("/v1/media09/press/status", headers=headers).status_code == 503


def test_never_in_production(monkeypatch):
    _, headers = setup(monkeypatch)
    monkeypatch.setenv("SCEC_ENV", "production")
    assert CLIENT.get("/v1/media09/press/status", headers=headers).status_code == 503


def test_legacy_identity_rejected(monkeypatch):
    _, headers = setup(monkeypatch)
    monkeypatch.setenv("SCEC_IDENTITY_MODE", "legacy")
    assert CLIENT.get("/v1/media09/press/status", headers=headers).status_code == 503


def test_anonymous_rejected(monkeypatch):
    setup(monkeypatch)
    assert CLIENT.get("/v1/media09/press/status").status_code == 401


def test_tenant_and_role_denied(monkeypatch):
    _, headers = setup(monkeypatch, role="viewer")
    assert CLIENT.get("/v1/media09/press/status", headers=headers).status_code == 403
    _, headers = setup(monkeypatch)
    headers["X-SCEC-Organization-ID"] = str(uuid4())
    assert CLIENT.get("/v1/media09/press/status", headers=headers).status_code == 403


def test_persistence_is_required(monkeypatch):
    _, headers = setup(monkeypatch)
    monkeypatch.setenv("SCEC_PERSISTENCE_ENABLED", "0")
    assert CLIENT.get("/v1/media09/press/status", headers=headers).status_code == 503


def test_valid_contract_stays_synthetic():
    p = press.PressInquiryCreate(**item())
    assert p.email == "press@example.org"
    assert p.consent_to_reply is True
    assert isinstance(press._id(uuid4(), p.idempotency_key), UUID)


@pytest.mark.parametrize("changes", [
    {"email": "real@gmail.com"},
    {"name": "Real Human"},
    {"synthetic": False},
    {"message": "<script>bad</script>"},
    {"message": "Visit https://example.org to proceed"},
    {"message": "Contact me at real@gmail.com"},
    {"subject": "Send to person@gmail.com"},
    {"company": "spammer"},
    {"consent_to_reply": False},
    {"privacy_notice_version": "INVALID"},
    {"arbitrary_publication_rights": True},
])
def test_invalid_submission_redacted(monkeypatch, changes):
    from app.media09_press import PressInquiryCreate
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PressInquiryCreate(**item(**changes))
    _, headers = setup(monkeypatch)
    value = item(**changes)
    # Route is called with valid principal but no DB access is needed for 422.
    response = CLIENT.post("/v1/media09/press/inquiries", headers=headers, json=value)
    assert response.status_code == 422, response.text
    assert "real@gmail.com" not in response.text
    assert "<script>" not in response.text


def test_create_api_receipt_has_no_personal_information(monkeypatch):
    _, headers = setup(monkeypatch)
    app.dependency_overrides[press.db_session] = fake_db
    seen = []
    monkeypatch.setattr(press, "create_record", lambda db, tenant, payload: (
        seen.append((tenant, payload.email)) or press._receipt(uuid4(), "new", 1, True)
    ))
    r = CLIENT.post("/v1/media09/press/inquiries", headers=headers, json=item())
    assert r.status_code == 201, r.text
    assert seen and seen[0][1] == "press@example.org"
    assert "press@example.org" not in r.text
    assert r.json()["outbound_sent"] is False and r.json()["crm_exported"] is False


def test_queue_list_and_detail_private(monkeypatch):
    _, headers = setup(monkeypatch)
    app.dependency_overrides[press.db_session] = fake_db
    ident = uuid4()
    monkeypatch.setattr(press, "list_records", lambda db, tenant, limit, offset: {
        "items": [{"inquiry_id": str(ident), "status": "new"}], "limit": limit,
        "offset": offset, "no_personal_data_in_list": True
    })
    monkeypatch.setattr(press, "detail_record", lambda db, tenant, inquiry_id: {
        "inquiry_id": str(inquiry_id), "email": "press@example.org",
        "message": "Synthetic inquiry only."
    })
    lst = CLIENT.get("/v1/media09/press/inquiries", headers=headers)
    assert lst.status_code == 200 and lst.json()["no_personal_data_in_list"] is True
    assert "press@example.org" not in lst.text
    d = CLIENT.get(f"/v1/media09/press/inquiries/{ident}", headers=headers)
    assert d.status_code == 200 and d.json()["email"] == "press@example.org"
    assert CLIENT.get("/v1/media09/press/inquiries", headers={}).status_code == 401


def test_review_transition_role_and_cas(monkeypatch):
    _, headers = setup(monkeypatch, role="contact_editor")
    app.dependency_overrides[press.db_session] = fake_db
    ident = uuid4()
    seen = []
    monkeypatch.setattr(press, "transition_record", lambda db, tenant, inquiry_id, change: (
        seen.append(change.status) or press._receipt(inquiry_id, change.status, 2, False)
    ))
    url = f"/v1/media09/press/inquiries/{ident}/status"
    assert CLIENT.patch(url, headers=headers, json={"status": "closed", "expected_version": 1}).status_code == 403
    r = CLIENT.patch(url, headers=headers, json={"status": "reviewing", "expected_version": 1})
    assert r.status_code == 200 and r.json()["status"] == "reviewing"
    _, admin_headers = setup(monkeypatch, role="administrator")
    r = CLIENT.patch(url, headers=admin_headers, json={"status": "closed", "expected_version": 1})
    assert r.status_code == 200
    assert seen == ["reviewing", "closed"]


def test_public_send_crm_export_always_blocked(monkeypatch):
    _, headers = setup(monkeypatch, role="administrator")
    for endpoint in ("public-submit", "send", "crm-export"):
        r = CLIENT.post("/v1/media09/press/" + endpoint, headers=headers, json=item())
        assert r.status_code == 503
    monkeypatch.setenv("SCEC_MEDIA09_PUBLIC_INTAKE_ENABLED", "1")
    assert CLIENT.post("/v1/media09/press/public-submit", headers=headers, json=item()).status_code == 503


def test_deterministic_dedupe_and_fingerprint():
    tenant = uuid4()
    a = press.PressInquiryCreate(**item())
    b = a.model_copy(deep=True)
    assert press._id(tenant, a.idempotency_key) == press._id(tenant, b.idempotency_key)
    assert press._fingerprint(a) == press._fingerprint(b)
    b.subject = "Different synthetic subject"
    assert press._fingerprint(a) != press._fingerprint(b)
    assert press._id(uuid4(), a.idempotency_key) != press._id(tenant, a.idempotency_key)


def test_database_contract_and_migration_registered():
    assert press_inquiry_details.name == "media09_press_inquiries"
    assert {"organization_id", "contact_id", "id", "request_digest", "notice_version", "status", "version"}.issubset(
        press_inquiry_details.c.keys()
    )


def test_reject_invalid_pagination_and_cas(monkeypatch):
    _, headers = setup(monkeypatch)
    r = CLIENT.get("/v1/media09/press/inquiries?limit=1000", headers=headers)
    assert r.status_code == 422
    assert CLIENT.patch("/v1/media09/press/inquiries/" + str(uuid4()) + "/status",
                        headers=headers, json={"status": "reviewing", "expected_version": 0}).status_code == 422


def test_idempotent_route_replay_is_http_200(monkeypatch):
    _, headers = setup(monkeypatch)
    app.dependency_overrides[press.db_session] = fake_db
    monkeypatch.setattr(press, "create_record", lambda db, tenant, payload: press._receipt(
        press._id(tenant, payload.idempotency_key), "reviewing", 2, False
    ))
    r = CLIENT.post("/v1/media09/press/inquiries", headers=headers, json=item())
    assert r.status_code == 200 and r.json()["created"] is False
    assert r.json()["outbound_sent"] is False


def test_database_unavailable_is_sanitized():
    from sqlalchemy.exc import SQLAlchemyError
    from fastapi import HTTPException

    class BrokenDb:
        def begin(self):
            raise SQLAlchemyError("private-password-and-db-details-must-not-escape")

    with pytest.raises(HTTPException) as exc:
        press.create_record(BrokenDb(), uuid4(), press.PressInquiryCreate(**item()))
    assert exc.value.status_code == 503
    assert "private-password" not in str(exc.value.detail)


def test_fixture_does_not_claim_real_consent():
    row = press.PressInquiryCreate(**item())
    assert press.NOTICE.startswith("MEDIA-09.1-SYNTHETIC")
    assert row.consent_to_reply is True
    assert row.email.endswith("@example.org")
