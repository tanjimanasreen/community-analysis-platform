"""Environment and stage configuration for community-analysis CDK."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, Final

ALLOWED_STAGES: Final[tuple[str, ...]] = ("dev", "prod")
DEFAULT_PROJECT_NAME: Final[str] = "community-analysis"
DEFAULT_REGION: Final[str] = "us-east-1"


@dataclass(frozen=True)
class StageConfig:
    """Configuration definition for a specific deployment stage."""

    stage_name: str
    project_name: str = DEFAULT_PROJECT_NAME
    account: str | None = None
    region: str = DEFAULT_REGION
    extra_tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.stage_name not in ALLOWED_STAGES:
            raise ValueError(
                f"Invalid stage '{self.stage_name}'. Allowed stages are: {', '.join(ALLOWED_STAGES)}"
            )

    @property
    def tags(self) -> Dict[str, str]:
        """Standard resource tags applied across all constructs in this stage."""
        base_tags = {
            "Project": self.project_name,
            "Environment": self.stage_name,
            "ManagedBy": "aws-cdk",
        }
        base_tags.update(self.extra_tags)
        return base_tags

    def format_stack_name(self, component: str) -> str:
        """Return standard stack name following `<project>-<stage>-<component>`."""
        return f"{self.project_name}-{self.stage_name}-{component}"


def get_stage_config(
    stage_name: str | None,
    account: str | None = None,
    region: str | None = None,
) -> StageConfig:
    """Resolve and validate configuration for the specified stage name.

    Fails fast if stage_name is missing or unrecognized.
    """
    if not stage_name or not stage_name.strip():
        raise ValueError(
            f"CDK stage is required. Use -c stage=dev or -c stage=prod. "
            f"Allowed stages: {', '.join(ALLOWED_STAGES)}"
        )

    normalized_stage = stage_name.strip().lower()
    if normalized_stage not in ALLOWED_STAGES:
        raise ValueError(
            f"Unknown stage '{stage_name}'. Allowed stages are: {', '.join(ALLOWED_STAGES)}"
        )

    resolved_account = account or os.environ.get("CDK_DEFAULT_ACCOUNT")
    resolved_region = region or os.environ.get("CDK_DEFAULT_REGION") or DEFAULT_REGION

    return StageConfig(
        stage_name=normalized_stage,
        account=resolved_account,
        region=resolved_region,
    )
