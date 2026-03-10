from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Source ──────────────────────────────────────────────────────────────────

class SourceCreate(BaseModel):
    slug: str = Field(..., pattern=r"^[a-z0-9_-]+$", max_length=64)
    display_name: str = Field(..., max_length=255)
    description: str | None = None
    active: bool = True


class SourceOut(BaseModel):
    id: int
    slug: str
    display_name: str
    description: str | None
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Run ─────────────────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    source_id: int


class RunPatch(BaseModel):
    status: str = Field(..., pattern=r"^(success|failed)$")
    records_ingested: int = 0
    records_failed: int = 0
    error_message: str | None = None


class RunOut(BaseModel):
    id: int
    source_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    records_ingested: int
    records_failed: int
    error_message: str | None

    model_config = {"from_attributes": True}


# ── Ingest / Record ──────────────────────────────────────────────────────────

class IngestRecord(BaseModel):
    source_slug: str
    run_id: int | None = None
    external_id: str | None = None
    record_type: str = Field(..., max_length=64)
    title: str | None = None
    author: str | None = None
    rating: float | None = Field(None, ge=0, le=10)
    status: str | None = None
    event_date: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class IngestBatch(BaseModel):
    records: list[IngestRecord] = Field(..., min_length=1, max_length=500)


class IngestResponse(BaseModel):
    accepted: int
    failed: int
    errors: list[str] = []


class RecordOut(BaseModel):
    id: int
    source_id: int
    run_id: int | None
    external_id: str | None
    record_type: str
    title: str | None
    author: str | None
    rating: float | None
    status: str | None
    event_date: datetime | None
    ingested_at: datetime

    model_config = {"from_attributes": True}
