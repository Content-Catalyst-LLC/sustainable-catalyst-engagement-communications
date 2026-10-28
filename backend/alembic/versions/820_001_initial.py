"""Initial canonical PostgreSQL schema. Never touches existing legacy databases.
Revision ID: 820_001
Revises:
"""
from alembic import op
from app.persistence.models import metadata
revision='820_001'
down_revision=None
branch_labels=None
depends_on=None

# Only the tables owned by this revision belong in its bootstrap. Alembic's
# env.py registers the later audit table on this same metadata object; creating
# all registered tables here causes 830_001 to create it a second time.
INITIAL_TABLE_NAMES = (
    'organizations', 'contacts', 'cases', 'inquiries', 'advisory_engagements',
    'newsletters', 'forms', 'surveys', 'submissions', 'tests', 'assessments',
    'engagement_events', 'import_batches',
)

def upgrade():
    connection=op.get_bind()
    metadata.create_all(
        bind=connection,
        tables=[metadata.tables[name] for name in INITIAL_TABLE_NAMES],
        checkfirst=False,
    )

def downgrade():
    raise RuntimeError('Destructive rollback intentionally disabled. Restore dedicated database snapshot or use documented clean rehearsal teardown.')
