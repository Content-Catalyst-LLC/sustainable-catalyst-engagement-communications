"""v8.5.0 additive advisory approval and provenance; forward only."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision='850_001'
down_revision='840_001'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('advisory_approvals',
        sa.Column('id',UUID(as_uuid=True),primary_key=True),
        sa.Column('organization_id',UUID(as_uuid=True),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('engagement_id',UUID(as_uuid=True),sa.ForeignKey('advisory_engagements.id'),nullable=False),
        sa.Column('requested_by',sa.String(120),nullable=False),
        sa.Column('state',sa.String(20),nullable=False),
        sa.Column('reviewed_by',sa.String(120)),
        sa.Column('requested_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('reviewed_at',sa.DateTime(timezone=True)),
        sa.Column('note',sa.String(2000)),
        sa.CheckConstraint("state IN ('pending','approved','rejected')",name='ck_advisory_approval_state'))
    op.create_index('ix_advisory_approvals_tenant_engagement','advisory_approvals',['organization_id','engagement_id'])
    op.create_index('ux_advisory_one_pending','advisory_approvals',['organization_id','engagement_id'],unique=True,postgresql_where=sa.text("state = 'pending'"))
    op.create_table('advisory_workflow_history',
        sa.Column('id',UUID(as_uuid=True),primary_key=True),
        sa.Column('organization_id',UUID(as_uuid=True),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('engagement_id',UUID(as_uuid=True),sa.ForeignKey('advisory_engagements.id'),nullable=False),
        sa.Column('event_type',sa.String(40),nullable=False),
        sa.Column('before_status',sa.String(30)),
        sa.Column('after_status',sa.String(30),nullable=False),
        sa.Column('actor_ref',sa.String(120),nullable=False),
        sa.Column('note',sa.String(2000)),
        sa.Column('occurred_at',sa.DateTime(timezone=True),nullable=False),
        sa.CheckConstraint("event_type IN ('created','approval_requested','approval_approved','approval_rejected','transition')",name='ck_advisory_event_type'))
    op.create_index('ix_advisory_history_tenant_engagement','advisory_workflow_history',['organization_id','engagement_id','occurred_at'])

def downgrade():
    raise RuntimeError('Destructive downgrade forbidden; restore verified backup')
