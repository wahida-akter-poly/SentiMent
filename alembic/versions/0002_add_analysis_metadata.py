"""Add analysis metadata fields

Revision ID: 0002_add_analysis_metadata
Revises: 0001_create_analyses
Create Date: 2026-09-26 04:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_analysis_metadata"
down_revision = "0001_create_analyses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("analyses")}
    if "model_sentiment" not in columns:
        op.add_column("analyses", sa.Column("model_sentiment", sa.String(length=20), nullable=True, server_default="neutral"))
    if "sentence_results" not in columns:
        op.add_column("analyses", sa.Column("sentence_results", sa.JSON(), nullable=True))
    if "aspects" not in columns:
        op.add_column("analyses", sa.Column("aspects", sa.JSON(), nullable=True))
    if "topics" not in columns:
        op.add_column("analyses", sa.Column("topics", sa.JSON(), nullable=True))
    if "evidence" not in columns:
        op.add_column("analyses", sa.Column("evidence", sa.JSON(), nullable=True))
    if "summary_text" not in columns:
        op.add_column("analyses", sa.Column("summary_text", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("analyses")}
    for column_name in [
        "model_sentiment",
        "sentence_results",
        "aspects",
        "topics",
        "evidence",
        "summary_text",
    ]:
        if column_name in columns:
            op.drop_column("analyses", column_name)
