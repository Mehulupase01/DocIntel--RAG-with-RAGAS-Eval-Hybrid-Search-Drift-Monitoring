"""Phase 1 foundation migration."""

from __future__ import annotations

from alembic import op

revision = "001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE document_status AS ENUM ('pending', 'ingesting', 'ready', 'failed'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE retrieval_strategy AS ENUM "
        "('vector_only', 'bm25_only', 'hybrid', 'hybrid_reranked'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE eval_run_status AS ENUM ('running', 'passed', 'failed', 'errored'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE drift_status AS ENUM ('ok', 'warning', 'alert'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP TYPE IF EXISTS drift_status")
    op.execute("DROP TYPE IF EXISTS eval_run_status")
    op.execute("DROP TYPE IF EXISTS retrieval_strategy")
    op.execute("DROP TYPE IF EXISTS document_status")
