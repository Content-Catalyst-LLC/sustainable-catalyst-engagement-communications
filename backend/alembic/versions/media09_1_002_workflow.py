"""Press assignment and optional provider outcome, within existing inquiry store."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = 'media09_1_002'
down_revision = 'media09_1_001'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('media09_press_inquiries', sa.Column('assigned_to', sa.String(200)))
    op.add_column('media09_press_inquiries', sa.Column('sync_result', JSONB))

def downgrade():
    raise RuntimeError('Destructive downgrade forbidden; restore verified backup')
