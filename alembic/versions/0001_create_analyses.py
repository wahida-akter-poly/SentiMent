"""create analyses table

Revision ID: 0001_create_analyses
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_analyses"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("analyses"):
        op.create_table(
            "analyses",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=True),
            sa.Column("sentiment", sa.String(length=20), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("probabilities", sa.JSON(), nullable=False),
            sa.Column("model_version", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_analyses_created_at", "analyses", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("analyses"):
        op.drop_index("ix_analyses_created_at", table_name="analyses")
        op.drop_table("analyses")
