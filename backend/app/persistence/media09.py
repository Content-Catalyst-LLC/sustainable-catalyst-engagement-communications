"""MEDIA-09.1 supplementary restricted Press inquiry fields.

Canonical Contact and Inquiry remain the records of authority. This table
stores only the synthetic Press-specific body and policy metadata.
"""
from sqlalchemy import Table, Column, String, DateTime, Boolean, Integer, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .models import metadata

press_inquiry_details = Table(
    "media09_press_inquiries", metadata,
    Column("id", UUID(as_uuid=True), ForeignKey("inquiries.id", ondelete="RESTRICT"), primary_key=True),
    Column("organization_id", UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
    Column("contact_id", UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False),
    Column("synthetic_only", Boolean, nullable=False, server_default="true"),
    Column("assigned_to", String(200)),
    Column("sync_result", JSONB),
    Column("kind", String(40), nullable=False),
    Column("body", String(800), nullable=False),
    Column("status", String(20), nullable=False),
    Column("version", Integer, nullable=False),
    Column("notice_version", String(80), nullable=False),
    Column("reply_consent", Boolean, nullable=False),
    Column("request_digest", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("kind IN ('press','research-collaboration','institutional-partnership','funding')", name="kind"),
    CheckConstraint("status IN ('new','reviewing','closed')", name="status"),
    CheckConstraint("version >= 1", name="version"),
    CheckConstraint("reply_consent = TRUE", name="reply_consent_synthetic"),
)
Index("ix_media09_press_tenant_created", press_inquiry_details.c.organization_id, press_inquiry_details.c.created_at)
Index("ix_media09_press_tenant_status", press_inquiry_details.c.organization_id, press_inquiry_details.c.status)
