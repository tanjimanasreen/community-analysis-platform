from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_run_catalog
from src.api.errors import InvalidManifestError
from src.api.schemas.runs import (
    ArtifactMetadata,
    ArtifactsResponse,
    RunDetail,
    RunsResponse,
    RunSummary,
    VerificationResponse,
)
from src.api.services.run_catalog import (
    RunCatalog,
    RunFilter,
    manifest_year_month,
)
from src.artifacts.models import RunStatus

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunsResponse)
def list_runs(
    platform: str | None = None,
    content_type: str | None = None,
    year: int | None = Query(default=None, ge=1),
    month: int | None = Query(default=None, ge=1, le=12),
    status: RunStatus | None = None,
    catalog: RunCatalog = Depends(get_run_catalog),
) -> RunsResponse:
    manifests = catalog.list_manifests(
        RunFilter(
            platform=platform,
            content_type=content_type,
            year=year,
            month=month,
            status=status,
        )
    )
    runs = [_summary(item) for item in manifests]
    return RunsResponse(runs=runs, total=len(runs))


@router.get("/{run_id}", response_model=RunDetail)
def get_run(run_id: str, catalog: RunCatalog = Depends(get_run_catalog)) -> RunDetail:
    manifest = catalog.get_manifest(run_id)
    return RunDetail(
        run_id=manifest.run_id,
        status=manifest.status.value,
        dataset=dict(manifest.dataset),
        code=dict(manifest.code),
        pipeline=dict(manifest.pipeline),
        artifact_count=len(manifest.artifacts),
        failure=dict(manifest.failure) if manifest.failure else None,
    )


@router.get("/{run_id}/artifacts", response_model=ArtifactsResponse)
def list_artifacts(
    run_id: str, catalog: RunCatalog = Depends(get_run_catalog)
) -> ArtifactsResponse:
    manifest = catalog.get_manifest(run_id)
    artifacts = [ArtifactMetadata(**item.to_dict()) for item in manifest.artifacts]
    return ArtifactsResponse(
        run_id=run_id,
        artifacts=artifacts,
        total=len(artifacts),
    )


@router.get("/{run_id}/verification", response_model=VerificationResponse)
def verify_run(
    run_id: str,
    deep: bool = Query(
        default=False,
        description="Re-hash and schema-check every artifact instead of using the fast dashboard check.",
    ),
    catalog: RunCatalog = Depends(get_run_catalog),
) -> VerificationResponse:
    try:
        manifest = catalog.verify(run_id, deep=deep)
    except InvalidManifestError as exc:
        return VerificationResponse(
            run_id=run_id,
            ok=False,
            status="invalid",
            checked_artifacts=0,
            error_code=_verification_code(exc.message),
            error=exc.message,
        )
    return VerificationResponse(
        run_id=run_id,
        ok=True,
        status=manifest.status.value,
        checked_artifacts=len(manifest.artifacts),
    )


def _summary(manifest) -> RunSummary:
    year, month = manifest_year_month(manifest)
    return RunSummary(
        run_id=manifest.run_id,
        status=manifest.status.value,
        platform=manifest.dataset.get("platform") or None,
        content_type=manifest.dataset.get("content_type") or None,
        date_start=manifest.dataset.get("date_start") or None,
        date_end=manifest.dataset.get("date_end") or None,
        year=year,
        month=month,
        started_at=manifest.pipeline.get("started_at") or None,
        completed_at=manifest.pipeline.get("completed_at") or None,
        artifact_count=len(manifest.artifacts),
    )


def _verification_code(message: str) -> str:
    normalized = message.lower()
    if "checksum mismatch" in normalized or "byte size mismatch" in normalized:
        return "ARTIFACT_CHECKSUM_MISMATCH"
    if "schema" in normalized:
        return "ARTIFACT_SCHEMA_MISMATCH"
    if "missing" in normalized:
        return "ARTIFACT_MISSING"
    if "path escapes" in normalized:
        return "ARTIFACT_PATH_VIOLATION"
    return "INVALID_MANIFEST"
