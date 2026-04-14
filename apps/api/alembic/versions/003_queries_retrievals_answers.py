"""Phase 3 queries, retrievals, answers, and citations migration."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_queries_retrievals_answers"
down_revision = "002_documents_and_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    retrieval_strategy_enum = postgresql.ENUM(
        "vector_only",
        "bm25_only",
        "hybrid",
        "hybrid_reranked",
        name="retrieval_strategy",
        create_type=False,
    )

    op.create_table(
        "queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("strategy", retrieval_strategy_enum, nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False),
        sa.Column("rerank_top_n", sa.Integer(), nullable=True),
        sa.Column("alpha", sa.Float(), nullable=True),
        sa.Column("rrf_k", sa.Integer(), nullable=True, server_default="60"),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "retrievals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("bm25_score", sa.Float(), nullable=True),
        sa.Column("vector_score", sa.Float(), nullable=True),
        sa.Column("fused_score", sa.Float(), nullable=True),
        sa.Column("rerank_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_retrievals_query_id_rank", "retrievals", ["query_id", "rank"], unique=False)

    op.create_table(
        "answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("query_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("queries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finish_reason", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_answers_query_id", "answers", ["query_id"], unique=False)
    op.create_index("ix_answers_created_at", "answers", ["created_at"], unique=False)

    op.create_table(
        "citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("answer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("answers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("span_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_citations_answer_id_ord", "citations", ["answer_id", "ordinal"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_citations_answer_id_ord", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_answers_created_at", table_name="answers")
    op.drop_index("ix_answers_query_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_retrievals_query_id_rank", table_name="retrievals")
    op.drop_table("retrievals")
    op.drop_table("queries")
