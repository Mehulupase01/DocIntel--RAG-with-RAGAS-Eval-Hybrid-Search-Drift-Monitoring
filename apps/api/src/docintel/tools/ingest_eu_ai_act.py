from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import httpx

from docintel.config import get_settings
from docintel.database import get_session_factory
from docintel.models.chunk import Chunk
from docintel.services.ingestion.pipeline import DocumentIngestionService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the EU AI Act PDF into DocIntel.")
    parser.add_argument("--path", type=str, help="Local path to a PDF")
    parser.add_argument("--title", type=str, default="EU AI Act")
    parser.add_argument("--source-uri", type=str, default=None)
    args = parser.parse_args()

    settings = get_settings()
    file_bytes: bytes
    source_uri = args.source_uri
    filename: str | None = None

    if args.path:
        path = Path(args.path).expanduser().resolve()
        file_bytes = path.read_bytes()
        source_uri = source_uri or str(path)
        filename = path.name
    elif settings.eu_ai_act_pdf_url:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(settings.eu_ai_act_pdf_url)
            response.raise_for_status()
            file_bytes = response.content
        source_uri = source_uri or settings.eu_ai_act_pdf_url
        filename = "eu_ai_act.pdf"
    else:
        raise SystemExit("Provide --path or set EU_AI_ACT_PDF_URL in the environment.")

    session_factory = get_session_factory()
    async with session_factory() as session:
        service = DocumentIngestionService(session)
        document = await service.ingest_document(
            file_bytes=file_bytes,
            title=args.title,
            source_uri=source_uri,
            filename=filename,
        )
        chunk_count = await session.scalar(select_count_chunks(document.id))
        print(
            f"ingested document_id={document.id} title={document.title!r} "
            f"status={document.status.value} page_count={document.page_count} chunks={int(chunk_count or 0)}"
        )


def select_count_chunks(document_id):
    from sqlalchemy import func, select

    return select(func.count(Chunk.id)).where(Chunk.document_id == document_id)


if __name__ == "__main__":
    asyncio.run(main())
