from __future__ import annotations

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.auth import require_api_key
from docintel.config import Settings, get_settings
from docintel.database import get_db, get_session_factory
from docintel.logging_setup import get_logger
from docintel.models.chunk import Chunk
from docintel.models.document import Document, DocumentStatus
from docintel.schemas.common import ErrorEnvelope, PageMeta, Paginated
from docintel.schemas.document import DocumentOut
from docintel.services.ingestion.pipeline import (
    DocumentBusyError,
    DocumentIngestionService,
    DocumentNotFoundError,
    DuplicateDocumentError,
    InvalidDocumentError,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorEnvelope},
        401: {"model": ErrorEnvelope},
        409: {"model": ErrorEnvelope},
        413: {"model": ErrorEnvelope},
    },
)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[None, Depends(require_api_key)],
    title: Annotated[str | None, Form()] = None,
    source_uri: Annotated[str | None, Form()] = None,
) -> DocumentOut:
    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_bytes:
        return _error_response(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "PAYLOAD_TOO_LARGE",
            f"PDF exceeds MAX_UPLOAD_BYTES ({settings.max_upload_bytes})",
        )

    service = DocumentIngestionService(db)
    try:
        document = await service.ingest_document(
            file_bytes=file_bytes,
            title=title,
            source_uri=source_uri,
            filename=file.filename,
        )
    except DuplicateDocumentError:
        return _error_response(
            status.HTTP_409_CONFLICT,
            "DUPLICATE_DOCUMENT",
            "A document with the same sha256 has already been ingested",
        )
    except InvalidDocumentError as exc:
        return _error_response(status.HTTP_400_BAD_REQUEST, "INVALID_FILE", str(exc))

    chunk_count = await _chunk_count_for_document(db, document.id)
    return _to_document_out(document, chunk_count)


@router.get("", response_model=Paginated[DocumentOut])
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
) -> Paginated[DocumentOut]:
    filters = []
    if status_filter is not None:
        filters.append(Document.status == status_filter)

    total = await db.scalar(select(func.count()).select_from(Document).where(*filters))
    stmt = (
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    documents = list((await db.scalars(stmt)).all())
    chunk_counts = await _chunk_counts(db, [document.id for document in documents])
    return Paginated[DocumentOut](
        data=[_to_document_out(document, chunk_counts.get(document.id, 0)) for document in documents],
        meta=PageMeta(page=page, per_page=per_page, total=total or 0),
    )


@router.get("/{document_id}", response_model=DocumentOut, responses={404: {"model": ErrorEnvelope}})
async def get_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentOut:
    document = await db.get(Document, document_id)
    if document is None:
        return _error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Document not found")

    return _to_document_out(document, await _chunk_count_for_document(db, document.id))


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorEnvelope}},
)
async def delete_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> Response:
    document = await db.get(Document, document_id)
    if document is None:
        return _error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Document not found")

    await db.delete(document)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{document_id}/reingest",
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorEnvelope}, 409: {"model": ErrorEnvelope}},
)
async def reingest_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> dict[str, str]:
    document = await db.get(Document, document_id)
    if document is None:
        return _error_response(status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Document not found")
    if document.status == DocumentStatus.INGESTING:
        return _error_response(status.HTTP_409_CONFLICT, "DOCUMENT_BUSY", "Document is already ingesting")

    document.status = DocumentStatus.INGESTING
    document.error_message = None
    db.add(document)
    await db.commit()

    asyncio.create_task(_run_reingest(document_id))
    return {"id": str(document_id), "status": DocumentStatus.INGESTING.value}


async def _run_reingest(document_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        service = DocumentIngestionService(session)
        try:
            await service.reingest_document(document_id)
        except (DocumentBusyError, DocumentNotFoundError, InvalidDocumentError):
            logger.exception("docintel.reingest_task_failed", document_id=str(document_id))
        except Exception:
            logger.exception("docintel.reingest_task_unhandled", document_id=str(document_id))


def _to_document_out(document: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut.model_validate(document, from_attributes=True).model_copy(
        update={"chunk_count": chunk_count}
    )


async def _chunk_count_for_document(db: AsyncSession, document_id: uuid.UUID) -> int:
    count = await db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id))
    return int(count or 0)


async def _chunk_counts(db: AsyncSession, document_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not document_ids:
        return {}

    stmt = (
        select(Chunk.document_id, func.count(Chunk.id))
        .where(Chunk.document_id.in_(document_ids))
        .group_by(Chunk.document_id)
    )
    rows = (await db.execute(stmt)).all()
    return {document_id: int(count) for document_id, count in rows}


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message, "detail": {}}})
