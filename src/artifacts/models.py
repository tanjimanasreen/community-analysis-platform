from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Mapping

RUN_MANIFEST_SCHEMA_VERSION = "1.0"


class RunStatus(str, Enum):
    """Lifecycle states persisted in a run manifest."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactCategory(str, Enum):
    """Stable artifact classes exposed to downstream consumers."""

    INTERMEDIATE = "intermediate"
    DATA = "data"
    REPORT = "report"


def _validate_sha256(value: str) -> str:
    normalized = str(value).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError("sha256 must be a 64-character hexadecimal string")
    return normalized


def _validate_relative_path(value: str) -> str:
    normalized = str(value).replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    windows_path = PureWindowsPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in path.parts
    ):
        raise ValueError("artifact path must be a non-empty relative path")
    return path.as_posix()


@dataclass(frozen=True)
class ArtifactRecord:
    """Portable record for one canonical artifact inside a run directory."""

    key: str
    path: str
    category: ArtifactCategory
    media_type: str
    schema_version: str
    sha256: str
    rows: int | None = None
    byte_size: int | None = None
    stage: str | None = None

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("artifact key must be non-empty")
        if not self.media_type.strip():
            raise ValueError("artifact media_type must be non-empty")
        if not str(self.schema_version).strip():
            raise ValueError("artifact schema_version must be non-empty")
        if self.rows is not None and self.rows < 0:
            raise ValueError("artifact rows must be non-negative")
        if self.byte_size is not None and self.byte_size < 0:
            raise ValueError("artifact byte_size must be non-negative")
        object.__setattr__(self, "path", _validate_relative_path(self.path))
        object.__setattr__(self, "sha256", _validate_sha256(self.sha256))
        if not isinstance(self.category, ArtifactCategory):
            object.__setattr__(self, "category", ArtifactCategory(self.category))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["category"] = self.category.value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ArtifactRecord":
        return cls(
            key=str(payload["key"]),
            path=str(payload["path"]),
            category=ArtifactCategory(str(payload["category"])),
            media_type=str(payload["media_type"]),
            schema_version=str(payload["schema_version"]),
            sha256=str(payload["sha256"]),
            rows=(int(payload["rows"]) if payload.get("rows") is not None else None),
            byte_size=(
                int(payload["byte_size"])
                if payload.get("byte_size") is not None
                else None
            ),
            stage=(str(payload["stage"]) if payload.get("stage") else None),
        )


@dataclass(frozen=True)
class RunManifest:
    """Versioned, portable description of one analytical pipeline run."""

    run_id: str
    status: RunStatus
    dataset: Mapping[str, Any]
    code: Mapping[str, Any]
    pipeline: Mapping[str, Any]
    artifacts: tuple[ArtifactRecord, ...] = field(default_factory=tuple)
    failure: Mapping[str, Any] | None = None
    schema_version: str = RUN_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id must be non-empty")
        if self.schema_version != RUN_MANIFEST_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported run manifest schema_version={self.schema_version!r}"
            )
        if not isinstance(self.status, RunStatus):
            object.__setattr__(self, "status", RunStatus(self.status))
        keys = [record.key for record in self.artifacts]
        if len(keys) != len(set(keys)):
            raise ValueError("run manifest artifact keys must be unique")
        if self.status is RunStatus.FAILED and not self.failure:
            raise ValueError("failed run manifests require failure metadata")
        if self.status is not RunStatus.FAILED and self.failure:
            raise ValueError("failure metadata is only valid for failed runs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "status": self.status.value,
            "dataset": dict(self.dataset),
            "code": dict(self.code),
            "pipeline": dict(self.pipeline),
            "artifacts": [record.to_dict() for record in self.artifacts],
            **({"failure": dict(self.failure)} if self.failure else {}),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RunManifest":
        return cls(
            schema_version=str(payload.get("schema_version", "")),
            run_id=str(payload["run_id"]),
            status=RunStatus(str(payload["status"])),
            dataset=dict(payload.get("dataset", {})),
            code=dict(payload.get("code", {})),
            pipeline=dict(payload.get("pipeline", {})),
            artifacts=tuple(
                ArtifactRecord.from_dict(item) for item in payload.get("artifacts", [])
            ),
            failure=(dict(payload["failure"]) if payload.get("failure") else None),
        )
