"""Append-only domain audit records; immutable at application layer."""
from sqlalchemy import Table, Column, String, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .models import metadata
audit_events=Table('engagement_audit_log',metadata,
 Column('id',UUID(as_uuid=True),primary_key=True,server_default=func.gen_random_uuid()),
 Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
 Column('record_type',String(60),nullable=False),
 Column('record_id',UUID(as_uuid=True),nullable=False),
 Column('operation',String(20),nullable=False),
 Column('recorded_at',DateTime(timezone=True),nullable=False),
 CheckConstraint("operation IN ('created','updated','imported')",name='operation'))
Index('ix_engagement_audit_org_record',audit_events.c.organization_id,audit_events.c.record_type,audit_events.c.record_id)
