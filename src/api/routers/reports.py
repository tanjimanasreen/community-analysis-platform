from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from src.api.dependencies import get_artifact_reader
from src.api.errors import ArtifactUnavailableError
from src.api.services.artifact_reader import ArtifactReader
from src.artifacts.models import ArtifactCategory

router = APIRouter(prefix="/runs", tags=["reports"])


@router.get("/{run_id}/report", response_class=FileResponse)
def get_report(
    run_id: str,
    reader: ArtifactReader = Depends(get_artifact_reader),
) -> FileResponse:
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
    path = reader.verified_path(run_id, record)
    return FileResponse(
        path,
        media_type=record.media_type,
        filename=path.name,
        content_disposition_type="inline",
    )


@router.get("/{run_id}/downloads/{artifact_key}", response_class=FileResponse)
def download_artifact(
    run_id: str,
    artifact_key: str,
    reader: ArtifactReader = Depends(get_artifact_reader),
) -> FileResponse:
    record = reader.get_record(run_id, artifact_key)
    if record.category is ArtifactCategory.INTERMEDIATE:
        raise ArtifactUnavailableError(run_id, artifact_key)
    path = reader.verified_path(run_id, record)
    return FileResponse(path, media_type=record.media_type, filename=path.name)
