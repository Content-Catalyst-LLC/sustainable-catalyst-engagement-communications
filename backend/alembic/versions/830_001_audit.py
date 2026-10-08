"""Append-only engagement audit ledger.
Revision ID: 830_001
Revises: 820_001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='830_001'
down_revision='820_001'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('engagement_audit_log',
       sa.Column('id',UUID(as_uuid=True),primary_key=True,server_default=sa.text('gen_random_uuid()')),
       sa.Column('organization_id',UUID(as_uuid=True),sa.ForeignKey('organizations.id'),nullable=False),
       sa.Column('record_type',sa.String(60),nullable=False),
       sa.Column('record_id',UUID(as_uuid=True),nullable=False),
       sa.Column('operation',sa.String(20),nullable=False),
       sa.Column('recorded_at',sa.DateTime(timezone=True),nullable=False),
       sa.CheckConstraint("operation IN ('created','updated','imported')",name='ck_engagement_audit_log_operation'))
    op.create_index('ix_engagement_audit_org_record','engagement_audit_log',['organization_id','record_type','record_id'])
def downgrade():
    raise RuntimeError('Destructive downgrades forbidden; restore from verified backup')
