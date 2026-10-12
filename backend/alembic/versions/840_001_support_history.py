"""Support history append-only ledger. Revision 840_001, revises 830_001."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
revision='840_001'
down_revision='830_001'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('support_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id',UUID(as_uuid=True),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('case_id',UUID(as_uuid=True),sa.ForeignKey('cases.id'),nullable=False),
        sa.Column('event_type',sa.String(40),nullable=False),
        sa.Column('from_status',sa.String(30)),
        sa.Column('to_status',sa.String(30),nullable=False),
        sa.Column('actor_ref',sa.String(120),nullable=False),
        sa.Column('note',sa.String(2000)),
        sa.Column('occurred_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("event_type IN ('created','transition','feedback')",name='ck_support_history_type'))
    op.create_index('ix_support_history_tenant_case','support_history',['organization_id','case_id','occurred_at'])

def downgrade():
    raise RuntimeError('Destructive downgrades forbidden; restore verified backup')
