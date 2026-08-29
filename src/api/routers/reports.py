from pathlib import Path

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse, StreamingResponse

from src.api.dependencies import get_artifact_reader
from src.api.errors import ArtifactUnavailableError
from src.api.services.artifact_reader import ArtifactReader
from src.artifacts.models import ArtifactCategory

router = APIRouter(prefix="/runs", tags=["reports"])


@router.get("/{run_id}/report")
def get_report(
    run_id: str,
    reader: ArtifactReader = Depends(get_artifact_reader),
) -> Response:
    candidates = reader.find_records(
        run_id, category=ArtifactCategory.REPORT, media_type="text/html"
    )
    candidates = [
        item
        for item in candidates
        if item.key in {"report_html", "report"} or item.path.endswith("report.html")
    ]
    if not candidates:
        raise ArtifactUnavailableError(run_id, "report_html")

    # Sort by priority: explicit key names before path-matched fallbacks
    def _report_priority(r) -> int:
        if r.key == "report_html":
            return 0
        if r.key == "report":
            return 1
        return 2

    record = sorted(candidates, key=_report_priority)[0]
    local_path = reader.get_local_path(run_id, record)
    if local_path is not None:
        reader.verified_path(run_id, record)
        return FileResponse(
            local_path,
            media_type=record.media_type,
            filename=local_path.name,
            content_disposition_type="inline",
        )

    # S3 / remote storage streaming
    reader.verified_path(run_id, record)
    filename = Path(record.path).name
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}
    if record.byte_size is not None:
        headers["Content-Length"] = str(record.byte_size)
    return StreamingResponse(
        reader.iter_bytes(run_id, record),
        media_type=record.media_type,
        headers=headers,
    )


@router.get("/{run_id}/downloads/{artifact_key}")
def download_artifact(
    run_id: str,
    artifact_key: str,
    reader: ArtifactReader = Depends(get_artifact_reader),
) -> Response:
    record = reader.get_record(run_id, artifact_key)
    if record.category is ArtifactCategory.INTERMEDIATE:
        raise ArtifactUnavailableError(run_id, artifact_key)

    local_path = reader.get_local_path(run_id, record)
    if local_path is not None:
        reader.verified_path(run_id, record)
        return FileResponse(
            local_path, media_type=record.media_type, filename=local_path.name
        )

    # S3 / remote storage streaming
    reader.verified_path(run_id, record)
    filename = Path(record.path).name
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if record.byte_size is not None:
        headers["Content-Length"] = str(record.byte_size)
    return StreamingResponse(
        reader.iter_bytes(run_id, record),
        media_type=record.media_type,
        headers=headers,
    )
