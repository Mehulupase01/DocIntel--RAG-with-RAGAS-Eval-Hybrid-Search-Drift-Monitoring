from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.config import get_settings
from docintel.logging_setup import get_logger
from docintel.models.chunk import Chunk
from docintel.models.document import Document, DocumentStatus

from .chunker import chunk_pages
from .embedder import get_embedder
from .pdf_loader import load_pdf_bytes_with_metadata

logger = get_logger(__name__)


class DuplicateDocumentError(Exception):
    pass


class DocumentBusyError(Exception):
    pass


class DocumentNotFoundError(Exception):
    pass


class InvalidDocumentError(Exception):
    pass


class DocumentIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def ingest_document(
        self,
        file_bytes: bytes,
        title: str | None,
        source_uri: str | None,
        filename: str | None = None,
    ) -> Document:
        if not file_bytes.startswith(b"%PDF"):
            raise InvalidDocumentError("The uploaded file is not a valid PDF")

        sha256 = hashlib.sha256(file_bytes).hexdigest()
        existing = await self.session.scalar(select(Document).where(Document.sha256 == sha256))
        if existing is not None:
            raise DuplicateDocumentError(existing.id)

        artifact_path = self._artifact_path(sha256, filename)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_bytes(file_bytes)

        document = Document(
            title=title or self._fallback_title(filename, source_uri),
            source_uri=source_uri,
            sha256=sha256,
            page_count=0,
            byte_size=len(file_bytes),
            status=DocumentStatus.INGESTING,
            metadata_json={"artifact_path": str(artifact_path), "original_filename": filename},
        )
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)

        try:
            pages, pdf_metadata = load_pdf_bytes_with_metadata(file_bytes)
            chunks = chunk_pages(
                pages,
                target_tokens=self.settings.chunk_target_tokens,
                overlap_tokens=self.settings.chunk_overlap_tokens,
            )
            if not chunks:
                raise InvalidDocumentError("The PDF does not contain extractable text")

            embeddings = get_embedder().embed_texts([chunk.text for chunk in chunks])
            document.title = title or pdf_metadata.get("Title") or self._fallback_title(filename, source_uri)
            document.page_count = len(pages)
            document.byte_size = len(file_bytes)
            document.status = DocumentStatus.READY
            document.error_message = None
            document.ingested_at = datetime.now(timezone.utc)
            document.metadata_json = {
                **document.metadata_json,
                "pdf_metadata": pdf_metadata,
                "page_heading_hints": {str(page.page_number): page.heading_hints for page in pages},
            }

            self.session.add_all(
                Chunk(
                    document_id=document.id,
                    ordinal=ordinal,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_path=chunk.section_path,
                    embedding=embedding,
                    metadata_json=chunk.metadata_json,
                )
                for ordinal, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            )
            await self.session.commit()
            await self.session.refresh(document)
            return document
        except Exception as exc:
            await self.session.rollback()
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            self.session.add(document)
            await self.session.commit()
            await self.session.refresh(document)
            logger.exception("docintel.ingestion_failed", document_id=str(document.id))
            raise

    async def reingest_document(self, document_id) -> Document:
        document = await self.session.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError(str(document_id))
        if document.status == DocumentStatus.INGESTING:
            raise DocumentBusyError(str(document_id))

        artifact_path = document.metadata_json.get("artifact_path")
        if not artifact_path:
            raise InvalidDocumentError("No stored artifact is available for reingestion")

        path = Path(artifact_path)
        if not path.exists():
            raise InvalidDocumentError("Stored artifact is missing from disk")

        document.status = DocumentStatus.INGESTING
        document.error_message = None
        self.session.add(document)
        await self.session.commit()
        await self.session.refresh(document)

        file_bytes = path.read_bytes()
        try:
            pages, pdf_metadata = load_pdf_bytes_with_metadata(file_bytes)
            chunks = chunk_pages(
                pages,
                target_tokens=self.settings.chunk_target_tokens,
                overlap_tokens=self.settings.chunk_overlap_tokens,
            )
            if not chunks:
                raise InvalidDocumentError("The PDF does not contain extractable text")

            embeddings = get_embedder().embed_texts([chunk.text for chunk in chunks])
            await self.session.execute(delete(Chunk).where(Chunk.document_id == document.id))
            document.page_count = len(pages)
            document.byte_size = len(file_bytes)
            document.status = DocumentStatus.READY
            document.error_message = None
            document.ingested_at = datetime.now(timezone.utc)
            document.metadata_json = {
                **document.metadata_json,
                "pdf_metadata": pdf_metadata,
                "page_heading_hints": {str(page.page_number): page.heading_hints for page in pages},
            }
            self.session.add_all(
                Chunk(
                    document_id=document.id,
                    ordinal=ordinal,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    char_start=chunk.char_start,
                    char_end=chunk.char_end,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_path=chunk.section_path,
                    embedding=embedding,
                    metadata_json=chunk.metadata_json,
                )
                for ordinal, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
            )
            await self.session.commit()
            await self.session.refresh(document)
            return document
        except Exception as exc:
            await self.session.rollback()
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            self.session.add(document)
            await self.session.commit()
            await self.session.refresh(document)
            logger.exception("docintel.reingestion_failed", document_id=str(document.id))
            raise

    def _artifact_path(self, sha256: str, filename: str | None) -> Path:
        extension = Path(filename).suffix if filename else ".pdf"
        extension = extension if extension.lower() == ".pdf" else ".pdf"
        return Path(self.settings.artifact_storage_path) / "documents" / f"{sha256}{extension}"

    @staticmethod
    def _fallback_title(filename: str | None, source_uri: str | None) -> str:
        if filename:
            return Path(filename).stem.replace("_", " ").strip() or "Untitled PDF"
        if source_uri:
            return Path(source_uri).stem.replace("_", " ").strip() or "Untitled PDF"
        return "Untitled PDF"
