from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    read_only: bool
    configured_runs: int


class RunMetadata(BaseModel):
    run_id: str
    config_path: str | None = None
    data_type: str
    content_type: str
    year: str
    output_base_path: str
    theme_output_dir: str
    longitudinal: bool


class RunsResponse(BaseModel):
    runs: list[RunMetadata]


class FacetsResponse(BaseModel):
    data_types: list[str]
    content_types: list[str]
    years: list[str]
    months: list[str]


class VerificationResponse(BaseModel):
    ok: bool
    checked_count: int = 0
    skipped_optional_count: int = 0
    error: str | None = None


class ArtifactMetadata(BaseModel):
    name: str
    classification: str
    relative_path: str
    exists: bool
    required: bool
    size_bytes: int | None = None
    modified_time: str | None = None
    required_columns: list[str] = Field(default_factory=list)


class ArtifactsResponse(BaseModel):
    artifacts: list[ArtifactMetadata]


class TableResponse(BaseModel):
    records: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    missing: bool = False
    artifact: str | None = None


class CommunitySummaryResponse(BaseModel):
    month: str
    matched_summary: dict[str, Any] | None = None
    user_message_counts: dict[str, Any] | None = None
    daily_message_stats: dict[str, Any] | None = None
    user_centrality: dict[str, Any] | None = None


class FileMetadata(BaseModel):
    category: str
    relative_path: str
    exists: bool
    size_bytes: int | None = None
    modified_time: str | None = None


class FilesResponse(BaseModel):
    files: list[FileMetadata]
