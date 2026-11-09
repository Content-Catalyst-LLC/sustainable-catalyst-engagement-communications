"""MEDIA-07 newsletter distribution foundation.

Offline, tenant-scoped planning only. No listmonk API requests, SMTP, subscriber
ingestion, scheduling, publication, or external delivery from Sustainable Catalyst.
The standalone listmonk staging stack is deployed/configured separately.
"""
import hashlib
import json
import os
import re
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .offline_staging import scope, seal

router = APIRouter(prefix="/v1/newsletter-studio", tags=["media07-offline"])
_scope = scope("SCEC_MEDIA07_STAGING_ENABLED")
HEX = re.compile(r"^[a-f0-9]{64}$")

class NewsletterPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=140)
    subject: str = Field(min_length=1, max_length=200)
    preheader: str = Field(default="", max_length=180)
    approved_revision_sha256: str = Field(min_length=64, max_length=64)
    channels: list[Literal["self_hosted_email", "substack_manual"]] = Field(min_length=1, max_length=2)

    @field_validator("approved_revision_sha256")
    @classmethod
    def valid_digest(cls, value):
        if not HEX.fullmatch(value):
            raise ValueError("SHA-256 required")
        return value

    @field_validator("channels")
    @classmethod
    def unique_channels(cls, channels):
        if len(channels) != len(set(channels)):
            raise ValueError("Duplicate channels")
        return channels

@router.get("/status")
def status(tenant=Depends(_scope)):
    return seal({
        "mode": "offline-newsletter-delivery-foundation",
        "primary_delivery": "self_hosted_listmonk",
        "optional_channel": "manual_substack_export",
        "listmonk_deployed_verified": False,
        "listmonk_api_access_enabled": False,
        "editor_integrated": False,
        "smtp_connected": False,
        "subscriber_import_enabled": False,
        "campaign_send_enabled": False,
    }, str(tenant), "MEDIA-07")

@router.post("/plan")
def plan(payload: NewsletterPlan, tenant=Depends(_scope)):
    # Preview the proposed destinations without contacting any service or
    # accepting subscriber data, raw HTML, secrets, or recipient addresses.
    raw = json.dumps(payload.model_dump(), sort_keys=True, separators=(",", ":"))
    return seal({
        "mode": "offline-delivery-plan",
        "title": payload.title,
        "subject": payload.subject,
        "preheader": payload.preheader,
        "approved_revision_sha256": payload.approved_revision_sha256,
        "input_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "channels": [
            {
                "channel": channel,
                "action": "listmonk_draft_only" if channel == "self_hosted_email" else "substack_manual_export",
                "status": "not_executed",
            } for channel in payload.channels
        ],
        "recipient_selection_performed": False,
        "listmonk_api_request_performed": False,
        "email_rendering_performed": False,
    }, str(tenant), "MEDIA-07")

@router.post("/send")
@router.post("/schedule")
@router.post("/publish")
@router.post("/subscribers/import")
@router.post("/listmonk/dispatch")
@router.post("/substack/publish")
def blocked(tenant=Depends(_scope)):
    raise HTTPException(503, "MEDIA-07 delivery and external publication not enabled")
