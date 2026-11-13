"""Default-disabled privacy operations; existing canonical Contact/Inquiry remain authoritative."""
from alembic import op
import sqlalchemy as sa
revision='media09_1_004'
down_revision='media09_1_003'
branch_labels=None
depends_on=None

def upgrade():
    from app.persistence.media09_privacy import PRIVACY_TABLES
    for table in PRIVACY_TABLES: table.create(op.get_bind(),checkfirst=False)
    for column in [
        sa.Column('privacy_notice_acknowledged',sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column('last_substantive_at',sa.DateTime(timezone=True)),
        sa.Column('retention_reviewed_at',sa.DateTime(timezone=True)),
        sa.Column('disposition',sa.String(24),nullable=False,server_default='routine'),
        sa.Column('follow_up_at',sa.DateTime(timezone=True)),
        sa.Column('follow_up_note',sa.String(500)),
    ]: op.add_column('media09_press_inquiries',column)
    op.execute('UPDATE media09_press_inquiries SET last_substantive_at=created_at')
    op.alter_column('media09_press_inquiries','last_substantive_at',nullable=False)
    # This legacy bit is retained only for historical synthetic clients. Real
    # inquiry processing records notice acknowledgment, never implied consent.
    connection=op.get_bind()
    for constraint in sa.inspect(connection).get_check_constraints('media09_press_inquiries'):
        if 'reply_consent' in constraint['sqltext']:
            op.drop_constraint(op.f(constraint['name']),'media09_press_inquiries',type_='check')
    op.create_check_constraint(op.f('ck_media09_real_no_inferred_consent'),'media09_press_inquiries',
        'synthetic_only OR reply_consent = FALSE')

def downgrade():
    raise RuntimeError('Destructive downgrade forbidden; restore verified backup and apply suppression before serving')
