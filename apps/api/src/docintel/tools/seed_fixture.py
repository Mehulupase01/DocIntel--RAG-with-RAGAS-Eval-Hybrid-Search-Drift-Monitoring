from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from docintel.database import get_session_factory
from docintel.models.chunk import Chunk
from docintel.models.document import Document


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Seed a draft eval fixture from ingested chunks.")
    parser.add_argument("--output", default="fixtures/eu_ai_act_qa_v1.generated.json")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args()

    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = (
            select(Chunk, Document.title)
            .join(Document, Document.id == Chunk.document_id)
            .order_by(Chunk.page_start.asc(), Chunk.ordinal.asc())
            .limit(args.limit)
        )
        rows = (await session.execute(stmt)).all()

    payload = {
        "version": "v0.1-draft",
        "source_doc_sha256": "fill-me",
        "cases": [
            {
                "id": f"draft-{index:03d}",
                "question": f"What does {chunk.section_path or title} say?",
                "ground_truth": chunk.text[:500],
                "expected_articles": [chunk.section_path] if chunk.section_path else [],
                "category": "draft",
            }
            for index, (chunk, title) in enumerate(rows, start=1)
        ],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote draft fixture to {output_path}")


if __name__ == "__main__":
    asyncio.run(_main())
