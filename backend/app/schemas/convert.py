from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadResponse(BaseModel):
    job_id: UUID
    status: Literal["queued"]
    stream_url: str

    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    id: UUID
    status: Literal["pending", "queued", "processing", "completed", "failed"]
    progress_percent: int = Field(0, ge=0, le=100)
    current_step: str
    original_filename: str
    target_format: Literal["docx", "xlsx"]
    page_count: int | None = None
    is_preview_only: bool = False
    preview_urls: list[str] = Field(default_factory=list)
    download_url: str | None = None
    error_message: str | None = None
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SSEProgressEvent(BaseModel):
    """Схема сериализации событий, публикуемых воркером в Redis Pub/Sub."""

    job_id: UUID
    status: Literal["pending", "queued", "processing", "completed", "failed"]
    progress_percent: int = Field(..., ge=0, le=100)
    current_step: str
    page_current: int | None = None
    page_total: int | None = None
    preview_urls: list[str] | None = None
    download_url: str | None = None
    is_preview_only: bool | None = None
    error: str | None = None


class ApiErrorResponse(BaseModel):
    error: str
    code: str
    upgrade_url: str | None = None
