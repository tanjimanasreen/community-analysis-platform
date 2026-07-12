import json
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence

@dataclass(frozen=True)
class DatasetIdentity:
    dataset_id: str
    path: str
    sha256: str
    dvc_pointer: str | None = None
    dvc_revision: str | None = None
    platform: str | None = None
    interaction_type: str | None = None
    period: str | None = None
    
    def __post_init__(self):
        if not self.sha256 or not self.sha256.strip():
            raise ValueError("sha256 must be a non-empty string")

@dataclass(frozen=True)
class ArtifactReference:
    path: str
    sha256: str
    media_type: str
    asset_key: str | None = None
    row_count: int | None = None
    byte_size: int | None = None

    def __post_init__(self):
        if not self.sha256 or not self.sha256.strip():
            raise ValueError("sha256 must be a non-empty string")

@dataclass(frozen=True)
class PipelineRunContext:
    pipeline_run_id: str
    git_commit: str
    config_digest: str
    output_root: str
    dataset_identities: tuple[DatasetIdentity, ...]
    prefect_flow_run_id: str | None = None
    dvc_revision: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
        
    @classmethod
    def create(cls, 
               pipeline_run_id: str,
               git_commit: str,
               config_digest: str,
               output_root: str,
               datasets: Sequence[DatasetIdentity],
               prefect_flow_run_id: str | None = None,
               dvc_revision: str | None = None) -> 'PipelineRunContext':
        return cls(
            pipeline_run_id=pipeline_run_id,
            git_commit=git_commit,
            config_digest=config_digest,
            output_root=output_root,
            dataset_identities=tuple(datasets),
            prefect_flow_run_id=prefect_flow_run_id,
            dvc_revision=dvc_revision
        )
