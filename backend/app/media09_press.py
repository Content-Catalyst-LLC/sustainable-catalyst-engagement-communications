"""MEDIA-09.1: isolated, durable *synthetic-only* first-party Press inquiry queue.

No public intake, no email, no HubSpot, no subscriber sync. Uses existing
canonical Contact/Inquiry PostgreSQL tables; only the supplementary Press detail
record is new. Input is restricted to synthetic-style fixtures, but those\nrestrictions cannot prove that free text contains no real personal data. Never\nsubmit actual personal information; all real public intake remains disabled.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID, NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .contact_service import config as persistence_config, session as db_session
from .contracts.canonical import Classification, Contact, Inquiry
from .identity import Principal, bound_mode, principal, tenant_for_principal
from .persistence.models import TABLES
from .persistence.audit import audit_events
from .persistence.media09 import press_inquiry_details

class RedactedPressRoute(APIRoute):
    """Prevent FastAPI 422 responses from echoing rejected messages or email."""
    def get_route_handler(self):
        original = super().get_route_handler()
        async def sanitized(request):
            try:
                return await original(request)
            except RequestValidationError:
                raise HTTPException(422, "Invalid synthetic Press submission") from None
        return sanitized


router = APIRouter(prefix="/v1/media09/press", tags=["media09-press-staging"], route_class=RedactedPressRoute)
NOTICE = "MEDIA-09.1-SYNTHETIC-NOTICE-V1"
SYNTHETIC_DOMAINS = ("example.org", "example.test", "example.invalid")
KINDS = ("press", "research-collaboration", "institutional-partnership", "funding")
MAX_PER_MINUTE = 5
EMAIL_RE = re.compile(r"^[A-Za-z0-9_.+%-]{1,64}@[A-Za-z0-9.-]{1,180}\.[A-Za-z]{2,20}$")
UNSAFE_RE = re.compile(r"<|>|https?://|www\.|[\x00-\x08\x0b\x0c\x0e-\x1f]", re.I)


def _safe_text(value: str) -> str:
    if UNSAFE_RE.search(value) or not value.strip():
        raise ValueError("Unsafe or empty text")
    return value


class PressInquiryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    synthetic: Literal[True]
    idempotency_key: UUID
    name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=6, max_length=254)
    subject: str = Field(min_length=5, max_length=160)
    message: str = Field(min_length=10, max_length=800)
    kind: Literal["press", "research-collaboration", "institutional-partnership", "funding"]
    privacy_notice_version: Literal["MEDIA-09.1-SYNTHETIC-NOTICE-V1"]
    consent_to_reply: Literal[True]
    company: str = Field(default="", max_length=0)  # honeypot, always blank

    @field_validator("name", "subject", "message")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("email")
    @classmethod
    def synthetic_email(cls, value: str) -> str:
        v = value.casefold()
        if not EMAIL_RE.fullmatch(v) or v.rsplit("@", 1)[-1] not in SYNTHETIC_DOMAINS:
            raise ValueError("Only reserved synthetic email domains permitted")
        return v

    @model_validator(mode="after")
    def fixture_only(self):
        if not self.name.casefold().startswith("synthetic "):
            raise ValueError("Synthetic name prefix required")
        if "@" in self.message or "@" in self.subject:
            raise ValueError("Contact details must not appear in free text")
        return self


class RealPressInquiryCreate(PressInquiryCreate):
    """Shared first-party contract after explicit owner release configuration."""
    synthetic: Literal[False]
    privacy_notice_version: str = Field(min_length=1,max_length=80)

    @field_validator("email")
    @classmethod
    def synthetic_email(cls, value: str) -> str:
        value=value.casefold()
        if not EMAIL_RE.fullmatch(value):
            raise ValueError("Valid reply email required")
        return value

    @model_validator(mode="after")
    def fixture_only(self):
        from .media09_release import approved_notice
        if self.privacy_notice_version != approved_notice()['version']:
            raise ValueError("Reload the approved privacy notice")
        return self


class PressStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["reviewing", "closed"]
    expected_version: int = Field(ge=1, le=10000)


def _actor(
    x_scec_organization_id: str | None = Header(default=None),
    actor: Principal | None = Depends(principal),
) -> tuple[UUID, Principal]:
    # Even an accidental production flag cannot enable real collection.
    if os.getenv("SCEC_MEDIA09_PRESS_STAGING_ENABLED", "0") != "1" or os.getenv("SCEC_ENV", "development") == "production":
        raise HTTPException(503, "MEDIA-09.1 isolated staging disabled")
    if not bound_mode():
        raise HTTPException(503, "Bound service identity required")
    tenant = tenant_for_principal(x_scec_organization_id, actor)
    _, allowed = persistence_config()  # dedicated DB + persistence flag
    if str(tenant) not in allowed:
        raise HTTPException(403, "Organization not allowlisted")
    if not actor.roles.intersection({"contact_editor", "administrator"}):
        raise HTTPException(403, "Private Press reviewer required")
    return tenant, actor


def _id(tenant: UUID, key: UUID) -> UUID:
    return uuid5(NAMESPACE_URL, f"sc-media09.1:inquiry:{tenant}:{key}")


def _fingerprint(payload: PressInquiryCreate) -> str:
    content = payload.model_dump(mode="json", exclude={"idempotency_key", "company"})
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _receipt(ident: UUID, status: str, version: int, created: bool, synthetic_only: bool=True) -> dict:
    return {
        "inquiry_id": str(ident), "status": status,
        "version": version, "created": created, "synthetic_only": synthetic_only,
        "outbound_sent": False, "crm_exported": False,
    }


def _advisory_lock(db: Session, tenant: UUID) -> None:
    # PostgreSQL transaction-scoped lock serializes tenant rate checks and
    # idempotent writes even across workers; no persistent lock allocation.
    key = int.from_bytes(hashlib.sha256(tenant.bytes).digest()[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def create_record(db: Session, tenant: UUID, payload: PressInquiryCreate) -> dict:
    ident = _id(tenant, payload.idempotency_key)
    fingerprint = _fingerprint(payload)
    now = datetime.now(timezone.utc)
    contact_id = uuid5(NAMESPACE_URL, f"sc-media09.1:contact:{tenant}:{payload.email}")
    try:
        with db.begin():
            _advisory_lock(db, tenant)
            previous = db.execute(
                select(press_inquiry_details.c.request_digest, press_inquiry_details.c.status, press_inquiry_details.c.version, press_inquiry_details.c.synthetic_only)
                .where(press_inquiry_details.c.id == ident, press_inquiry_details.c.organization_id == tenant)
            ).mappings().first()
            if previous:
                if not hmac.compare_digest(previous["request_digest"], fingerprint):
                    raise HTTPException(409, "Idempotency key reused with different content")
                return _receipt(ident, previous["status"], previous["version"], False, previous["synthetic_only"])
            if db.execute(select(TABLES["organizations"].c.id).where(TABLES["organizations"].c.id == tenant)).scalar_one_or_none() is None:
                raise HTTPException(422, "Staging organization must be registered first")
            recent = db.execute(
                select(func.count()).select_from(press_inquiry_details)
                .where(
                    press_inquiry_details.c.organization_id == tenant,
                    press_inquiry_details.c.created_at >= now - timedelta(minutes=1),
                )
            ).scalar_one()
            if recent >= MAX_PER_MINUTE:
                raise HTTPException(429, "Synthetic intake rate limit exceeded")
            existing_contact = db.execute(select(TABLES["contacts"].c.id).where(
                TABLES["contacts"].c.organization_id == tenant,
                func.lower(TABLES["contacts"].c.payload["email"].astext) == payload.email
            ).order_by(TABLES["contacts"].c.created_at, TABLES["contacts"].c.id).limit(1)).scalar_one_or_none()
            if existing_contact:
                contact_id = existing_contact
            contact = Contact(id=contact_id, organization_id=tenant, classification=Classification.restricted,
                              display_name=payload.name, email=payload.email, marketing_consent=False,
                              created_at=now, updated_at=now)
            inquiry = Inquiry(id=ident, organization_id=tenant, classification=Classification.restricted,
                              subject=payload.subject, status="new", contact_id=contact_id,
                              created_at=now, updated_at=now)
            for kind, entity in (("contacts", contact), ("inquiries", inquiry)):
                if kind == "contacts" and existing_contact:
                    continue
                db.execute(insert(TABLES[kind]).values(
                    id=entity.id, organization_id=tenant, schema_version=entity.schema_version,
                    classification=entity.classification.value,
                    created_at=now, updated_at=now, payload=entity.model_dump(mode="json"),
                ))
            db.execute(insert(press_inquiry_details).values(
                id=ident, organization_id=tenant, contact_id=contact_id,
                kind=payload.kind, body=payload.message, status="new", version=1,
                notice_version=payload.privacy_notice_version, reply_consent=True,
                request_digest=fingerprint, synthetic_only=payload.synthetic, created_at=now, updated_at=now,
            ))
            for record_type, record_id in (("contacts", contact_id), ("inquiries", ident), ("press_inquiries", ident)):
                if record_type == "contacts" and existing_contact:
                    continue
                db.execute(insert(audit_events).values(
                    organization_id=tenant, record_type=record_type,
                    record_id=record_id, operation="created", recorded_at=now,
                ))
    except IntegrityError:
        raise HTTPException(409, "Conflicting or incomplete staging record") from None
    except SQLAlchemyError:
        raise HTTPException(503, "Staging storage unavailable") from None
    return _receipt(ident, "new", 1, True, payload.synthetic)


def _joined(tenant: UUID):
    d = press_inquiry_details
    return (
        select(d, TABLES["inquiries"].c.payload.label("inquiry"),
               TABLES["contacts"].c.payload.label("contact"))
        .join(TABLES["inquiries"], TABLES["inquiries"].c.id == d.c.id)
        .join(TABLES["contacts"], TABLES["contacts"].c.id == d.c.contact_id)
        .where(d.c.organization_id == tenant,
               TABLES["inquiries"].c.organization_id == tenant,
               TABLES["contacts"].c.organization_id == tenant)
    )


def detail_record(db: Session, tenant: UUID, ident: UUID) -> dict:
    try:
        row = db.execute(_joined(tenant).where(press_inquiry_details.c.id == ident)).mappings().first()
    except SQLAlchemyError:
        raise HTTPException(503, "Staging storage unavailable") from None
    if row is None:
        raise HTTPException(404, "Inquiry not found")
    return {
        **_receipt(ident, row["status"], row["version"], False, row["synthetic_only"]),
        "kind": row["kind"], "subject": row["inquiry"]["subject"],
        "name": row["contact"]["display_name"], "email": row["contact"]["email"],
        "message": row["body"], "privacy_notice_version": row["notice_version"],
        "consent_to_reply": row["reply_consent"],
        "marketing_consent": False,
        "assigned_to": row["assigned_to"], "sync_result": row["sync_result"],
    }


def list_records(db: Session, tenant: UUID, limit: int, offset: int) -> dict:
    try:
        rows = db.execute(
            _joined(tenant).order_by(press_inquiry_details.c.created_at.desc(), press_inquiry_details.c.id)
            .limit(limit).offset(offset)
        ).mappings().all()
    except SQLAlchemyError:
        raise HTTPException(503, "Staging storage unavailable") from None
    return {"items": [
        {"inquiry_id": str(row["id"]), "kind": row["kind"],
         "subject": row["inquiry"]["subject"], "status": row["status"],
         "version": row["version"], "assigned_to": row["assigned_to"], "synthetic_only": row["synthetic_only"]}
        for row in rows
    ], "limit": limit, "offset": offset, "no_personal_data_in_list": all(row["synthetic_only"] for row in rows)}


def transition_record(db: Session, tenant: UUID, ident: UUID, change: PressStatusChange) -> dict:
    now = datetime.now(timezone.utc)
    try:
        with db.begin():
            _advisory_lock(db, tenant)
            row = db.execute(
                _joined(tenant).where(press_inquiry_details.c.id == ident)
            ).mappings().first()
            if row is None:
                raise HTTPException(404, "Inquiry not found")
            if row["version"] != change.expected_version:
                raise HTTPException(409, "Stale inbox revision")
            allowed = {"new": {"reviewing", "closed"}, "reviewing": {"closed"}, "closed": set()}
            if change.status not in allowed[row["status"]]:
                raise HTTPException(409, "Invalid status transition")
            updated = db.execute(
                update(press_inquiry_details)
                .where(press_inquiry_details.c.id == ident,
                       press_inquiry_details.c.organization_id == tenant,
                       press_inquiry_details.c.version == change.expected_version)
                .values(status=change.status, version=change.expected_version + 1, updated_at=now)
            )
            if updated.rowcount != 1:
                raise HTTPException(409, "Concurrent review conflict")
            updated_inquiry = dict(row["inquiry"])
            updated_inquiry["status"] = change.status
            updated_inquiry["updated_at"] = now.isoformat()
            db.execute(
                update(TABLES["inquiries"])
                .where(TABLES["inquiries"].c.id == ident, TABLES["inquiries"].c.organization_id == tenant)
                .values(payload=updated_inquiry, updated_at=now)
            )
            db.execute(insert(audit_events).values(
                organization_id=tenant, record_type="press_inquiries",
                record_id=ident, operation="updated", recorded_at=now,
            ))
    except IntegrityError:
        raise HTTPException(409, "Conflicting review update") from None
    except SQLAlchemyError:
        raise HTTPException(503, "Staging storage unavailable") from None
    return _receipt(ident, change.status, change.expected_version + 1, False, row["synthetic_only"])


@router.get("/status")
def status(context=Depends(_actor)):
    tenant, _ = context
    return {"build": "MEDIA-09.1", "organization_id": str(tenant),
            "staging": True, "synthetic_only": True, "public_intake_enabled": False,
            "hubspot_connected": False, "outbound_enabled": False,
            "private_queue_feature_configured": True,
            "postgres_acceptance_verified": False}


@router.get("/form-spec")
def form_spec(context=Depends(_actor)):
    return {"privacy_notice_version": NOTICE,
            "notice": "Synthetic staging only. Do not provide real personal data. No messages are sent.",
            "fields": ["name", "email", "subject", "message", "kind", "consent_to_reply"],
            "honeypot": "company", "public_submission_url": None,
            "real_personal_data_accepted": False}


@router.post("/inquiries", status_code=201)
def create(payload: PressInquiryCreate, response: Response, context=Depends(_actor), db: Session=Depends(db_session)):
    tenant, _ = context
    result = create_record(db, tenant, payload)
    if not result["created"]:
        response.status_code = 200  # Idempotent replay, not another new record.
    return result


@router.get("/inquiries")
def queue(limit: int=Query(20, ge=1, le=50), offset: int=Query(0, ge=0, le=100000),
          context=Depends(_actor), db: Session=Depends(db_session)):
    tenant, _ = context
    return list_records(db, tenant, limit, offset)


@router.get("/inquiries/{inquiry_id}")
def detail(inquiry_id: UUID, context=Depends(_actor), db: Session=Depends(db_session)):
    tenant, _ = context
    return detail_record(db, tenant, inquiry_id)


@router.patch("/inquiries/{inquiry_id}/status")
def change_status(inquiry_id: UUID, payload: PressStatusChange, context=Depends(_actor),
                  db: Session=Depends(db_session)):
    tenant, actor = context
    if payload.status == "closed" and "administrator" not in actor.roles:
        raise HTTPException(403, "Administrator approval required to close")
    return transition_record(db, tenant, inquiry_id, payload)


@router.post("/public-submit")
@router.post("/send")
@router.post("/crm-export")
def blocked():
    raise HTTPException(503, "Public submission, sending and CRM export are not enabled")
