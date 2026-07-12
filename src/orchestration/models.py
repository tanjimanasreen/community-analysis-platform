import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Mapping, Sequence, Optional

def _validate_sha256(val: str) -> str:
    if not val or not isinstance(val, str):
        raise ValueError("sha256 must be a non-empty string")
    val = val.lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", val):
        raise ValueError(f"sha256 must be a 64-character hexadecimal string, got '{val}'")
    return val

@dataclass(frozen=True)
class ValidatedRunConfiguration:
    config_digest: str
    output_root: str
    raw_config: Mapping[str, Any]

@dataclass(frozen=True)
class DatasetIdentity:
    dataset_id: str
    path: str
    sha256: str
    dvc_pointer: str | None = None
    dvc_revision: str | None = None
    platform: str | None = None
    identity_source: Optional[str] = None
    interaction_type: str | None = None
    period: str | None = None
    
    def __post_init__(self):
        object.__setattr__(self, "sha256", _validate_sha256(self.sha256))

@dataclass(frozen=True)
class ArtifactReference:
    path: str
    sha256: str
    media_type: str
    asset_key: str | None = None
    row_count: int | None = None
    byte_size: int | None = None

    def __post_init__(self):
        object.__setattr__(self, "sha256", _validate_sha256(self.sha256))

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
