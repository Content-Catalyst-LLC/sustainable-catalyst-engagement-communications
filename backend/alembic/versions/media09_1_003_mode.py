"""Record whether an inquiry is synthetic, without a second contact store."""
from alembic import op
import sqlalchemy as sa
revision='media09_1_003'
down_revision='media09_1_002'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('media09_press_inquiries',sa.Column('synthetic_only',sa.Boolean(),nullable=False,server_default=sa.true()))

def downgrade():
    raise RuntimeError('Destructive downgrade forbidden; restore verified backup')
