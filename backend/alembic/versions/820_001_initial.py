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

def upgrade():
    connection=op.get_bind()
    metadata.create_all(bind=connection,checkfirst=False)

def downgrade():
    raise RuntimeError('Destructive rollback intentionally disabled. Restore dedicated database snapshot or use documented clean rehearsal teardown.')
