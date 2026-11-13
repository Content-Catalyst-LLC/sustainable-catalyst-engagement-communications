"""Operational privacy records in the existing Media database; no identity store."""
from sqlalchemy import Table, Column, String, DateTime, Integer, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .models import metadata

rights_requests=Table('media09_rights_requests',metadata,
    Column('id',UUID(as_uuid=True),primary_key=True),
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
    Column('requester_email',String(254)),Column('kind',String(24),nullable=False),
    Column('contact_id',UUID(as_uuid=True)),Column('synthetic_only',Boolean,nullable=False),
    Column('status',String(24),nullable=False),Column('version',Integer,nullable=False),
    Column('verification_ref',String(120)),Column('response_ref',String(120)),
    Column('extension_ref',String(120)),Column('received_at',DateTime(timezone=True),nullable=False),
    Column('due_at',DateTime(timezone=True),nullable=False),Column('responded_at',DateTime(timezone=True)),
    Column('closed_at',DateTime(timezone=True)),Column('erasure_receipt',UUID(as_uuid=True)),
)
legal_holds=Table('media09_legal_holds',metadata,
    Column('id',UUID(as_uuid=True),primary_key=True),
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
    Column('contact_id',UUID(as_uuid=True),nullable=False),Column('reason',String(32),nullable=False),
    Column('case_ref',String(120),nullable=False),Column('review_at',DateTime(timezone=True),nullable=False),
    Column('created_at',DateTime(timezone=True),nullable=False),Column('released_at',DateTime(timezone=True)),
    Column('release_ref',String(120)),Column('version',Integer,nullable=False),
)
restrictions=Table('media09_privacy_restrictions',metadata,
    Column('contact_id',UUID(as_uuid=True),primary_key=True),
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
    Column('active',Boolean,nullable=False),Column('updated_at',DateTime(timezone=True),nullable=False),
)
attachments=Table('media09_attachments',metadata,
    Column('id',UUID(as_uuid=True),primary_key=True),
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
    Column('inquiry_id',UUID(as_uuid=True),ForeignKey('inquiries.id'),nullable=False),
    Column('object_key',String(120),nullable=False),Column('created_at',DateTime(timezone=True),nullable=False),
)
privacy_state=Table('media09_privacy_state',metadata,
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),primary_key=True),
    Column('generation',Integer,nullable=False),
)
deletion_receipts=Table('media09_deletion_receipts',metadata,
    Column('id',UUID(as_uuid=True),primary_key=True),
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
    Column('reason',String(24),nullable=False),Column('counts',JSONB,nullable=False),
    Column('recorded_at',DateTime(timezone=True),nullable=False),
)
backups=Table('media09_backup_inventory',metadata,
    Column('id',UUID(as_uuid=True),primary_key=True),
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),nullable=False),
    Column('object_key',String(80),nullable=False),Column('sha256',String(64),nullable=False),
    Column('generation',Integer,nullable=False),Column('created_at',DateTime(timezone=True),nullable=False),
    Column('expires_at',DateTime(timezone=True),nullable=False),Column('expired_at',DateTime(timezone=True)),
)
PRIVACY_TABLES=(rights_requests,legal_holds,restrictions,attachments,privacy_state,deletion_receipts,backups)

company_syncs=Table('media09_company_syncs',metadata,
    Column('organization_id',UUID(as_uuid=True),ForeignKey('organizations.id'),primary_key=True),
    Column('outcome',JSONB,nullable=False),Column('updated_at',DateTime(timezone=True),nullable=False),
)
PRIVACY_TABLES=PRIVACY_TABLES+(company_syncs,)
