"""Time-bounded reviewed continuing-purpose exceptions, never inferred from edits."""
from alembic import op
import sqlalchemy as sa
revision='media09_1_005'
down_revision='media09_1_004'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('media09_press_inquiries',sa.Column('retention_exception_ref',sa.String(120)))
    op.add_column('media09_press_inquiries',sa.Column('retention_exception_until',sa.DateTime(timezone=True)))

def downgrade():
    raise RuntimeError('Destructive downgrade forbidden; restore verified backup with suppression')
