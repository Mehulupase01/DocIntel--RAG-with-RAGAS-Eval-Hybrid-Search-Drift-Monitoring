from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from docintel.models.document import DocumentStatus
from docintel.schemas.common import Paginated


class DocumentCreate(BaseModel):
    title: str | None = None
    source_uri: str | None = None


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    source_uri: str | None
    sha256: str
    page_count: int
    byte_size: int
    status: DocumentStatus
    error_message: str | None
    metadata_json: dict
    ingested_at: datetime | None
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)


DocumentList = Paginated[DocumentOut]
