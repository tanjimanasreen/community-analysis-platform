import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Optional, Sequence

from src.tracking.contracts import TrackingRunReference


def _validate_sha256(value: str) -> str:
    if not value or not isinstance(value, str):
        raise ValueError("sha256 must be a non-empty string")
    normalized = value.lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized):
        raise ValueError(
            "sha256 must be a 64-character hexadecimal string, "
            f"got '{normalized}'"
        )
    return normalized


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
    dvc_content_hash: str | None = None
    dvc_revision: str | None = None
    platform: str | None = None
    identity_source: Optional[str] = None
    interaction_type: str | None = None
    period: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "sha256", _validate_sha256(self.sha256))


@dataclass(frozen=True)
class ArtifactReference:
    path: str
    sha256: str
    media_type: str
    asset_key: str | None = None
    row_count: int | None = None
    byte_size: int | None = None

    def __post_init__(self) -> None:
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
    def create(
        cls,
        pipeline_run_id: str,
        git_commit: str,
        config_digest: str,
        output_root: str,
        datasets: Sequence[DatasetIdentity],
        prefect_flow_run_id: str | None = None,
        dvc_revision: str | None = None,
    ) -> "PipelineRunContext":
        return cls(
            pipeline_run_id=pipeline_run_id,
            git_commit=git_commit,
            config_digest=config_digest,
            output_root=output_root,
            dataset_identities=tuple(datasets),
            prefect_flow_run_id=prefect_flow_run_id,
            dvc_revision=dvc_revision,
        )


@dataclass(frozen=True)
class PipelineRunResult:
    context: PipelineRunContext
    artifacts: Sequence[ArtifactReference]
    tracking: TrackingRunReference | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TopicInputBundle:
    absolute_community_messages: ArtifactReference
    weighted_community_messages: ArtifactReference
    matched_communities: ArtifactReference
    partial_matched_communities: ArtifactReference | None
    allowed_input_roots: tuple[str, ...] | None = None


@dataclass(frozen=True)
class TopicOutputBundle:
    lda_scores: ArtifactReference
    matched_communities_topics: ArtifactReference | None
    partial_matched_communities_topics: ArtifactReference | None
    theme_inputs: tuple[ArtifactReference, ...]


@dataclass(frozen=True)
class ThemeInputBundle:
    monthly_topic_outputs: Mapping[str, ArtifactReference]
    allowed_input_roots: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ThemeOutputBundle:
    themes: tuple[ArtifactReference, ...]
    community_transitions: ArtifactReference | None
    visualizations: tuple[ArtifactReference, ...]
    provider_run_summary: ArtifactReference | None
