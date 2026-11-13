"""MEDIA-09.1: additive restricted synthetic Press queue; never migrate production without approval."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "media09_1_001"
down_revision = "850_001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "media09_press_inquiries",
        sa.Column("id", UUID(as_uuid=True), sa.ForeignKey("inquiries.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("contact_id", UUID(as_uuid=True), sa.ForeignKey("contacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("body", sa.String(800), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("notice_version", sa.String(80), nullable=False),
        sa.Column("reply_consent", sa.Boolean(), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('press','research-collaboration','institutional-partnership','funding')", name="ck_media09_press_inquiries_kind"),
        sa.CheckConstraint("status IN ('new','reviewing','closed')", name="ck_media09_press_inquiries_status"),
        sa.CheckConstraint("version >= 1", name="ck_media09_press_inquiries_version"),
        sa.CheckConstraint("reply_consent = TRUE", name="ck_media09_press_inquiries_reply_consent_synthetic"),
    )
    op.create_index("ix_media09_press_tenant_created", "media09_press_inquiries", ["organization_id", "created_at"])
    op.create_index("ix_media09_press_tenant_status", "media09_press_inquiries", ["organization_id", "status"])

def downgrade():
    raise RuntimeError("Destructive MEDIA-09.1 downgrade forbidden; restore independently verified backup")
