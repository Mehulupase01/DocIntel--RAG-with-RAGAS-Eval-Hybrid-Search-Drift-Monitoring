"""Phase 7 drift reports migration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_drift_reports"
down_revision = "004_eval_runs_and_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    drift_status_enum = postgresql.ENUM(
        "ok",
        "warning",
        "alert",
        name="drift_status",
        create_type=False,
    )

    op.create_table(
        "drift_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding_drift_score", sa.Float(), nullable=True),
        sa.Column("query_drift_score", sa.Float(), nullable=True),
        sa.Column("retrieval_quality_delta", sa.Float(), nullable=True),
        sa.Column("status", drift_status_enum, nullable=False),
        sa.Column("html_path", sa.String(length=1024), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_table("drift_reports")
