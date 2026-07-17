from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HealthResponse(StrictModel):
    status: str
    read_only: bool
    schema_version: str


class RunSummary(StrictModel):
    run_id: str
    status: str
    platform: str | None = None
    content_type: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    year: int | None = None
    month: int | None = None
    started_at: str | None = None
    completed_at: str | None = None
    artifact_count: int


class RunsResponse(StrictModel):
    runs: list[RunSummary]
    total: int


class RunDetail(StrictModel):
    run_id: str
    status: str
    dataset: dict[str, Any]
    code: dict[str, Any]
    pipeline: dict[str, Any]
    artifact_count: int
    failure: dict[str, Any] | None = None


class ArtifactMetadata(StrictModel):
    key: str
    path: str
    category: str
    media_type: str
    schema_version: str
    sha256: str
    rows: int | None = None
    byte_size: int | None = None
    stage: str | None = None


class ArtifactsResponse(StrictModel):
    run_id: str
    artifacts: list[ArtifactMetadata]
    total: int


class VerificationResponse(StrictModel):
    run_id: str
    ok: bool
    status: str
    checked_artifacts: int
    error_code: str | None = None
    error: str | None = None
