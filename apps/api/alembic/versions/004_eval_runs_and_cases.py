"""Phase 5 eval runs and cases migration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_eval_runs_and_cases"
down_revision = "003_queries_retrievals_answers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    eval_run_status_enum = postgresql.ENUM(
        "running",
        "passed",
        "failed",
        "errored",
        name="eval_run_status",
        create_type=False,
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("suite_version", sa.String(length=32), nullable=False),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("generation_model", sa.String(length=128), nullable=False),
        sa.Column("judge_model", sa.String(length=128), nullable=False),
        sa.Column("retrieval_strategy", sa.String(length=64), nullable=False),
        sa.Column("status", eval_run_status_enum, nullable=False),
        sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cases_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("faithfulness_mean", sa.Float(), nullable=True),
        sa.Column("context_precision_mean", sa.Float(), nullable=True),
        sa.Column("context_recall_mean", sa.Float(), nullable=True),
        sa.Column("answer_relevancy_mean", sa.Float(), nullable=True),
        sa.Column("thresholds_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "eval_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fixture_case_id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("ground_truth", sa.Text(), nullable=False),
        sa.Column("generated_answer", sa.Text(), nullable=False),
        sa.Column("contexts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("faithfulness", sa.Float(), nullable=True),
        sa.Column("context_precision", sa.Float(), nullable=True),
        sa.Column("context_recall", sa.Float(), nullable=True),
        sa.Column("answer_relevancy", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_eval_cases_run_id", "eval_cases", ["run_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_eval_cases_run_id", table_name="eval_cases")
    op.drop_table("eval_cases")
    op.drop_table("eval_runs")
