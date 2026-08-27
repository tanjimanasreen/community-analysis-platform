"""Baseline empty stack definition for CDK verification."""

from __future__ import annotations

import aws_cdk as cdk
from constructs import Construct


class CommunityAnalysisBaselineStack(cdk.Stack):
    """Baseline stack for the community-analysis platform.

    Contains no application resources. Used to verify synthesis, tagging,
    and stage configuration before component stacks (storage, batch, api) are introduced.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        env: cdk.Environment | None = None,
        description: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(
            scope,
            construct_id,
            env=env,
            description=description,
            **kwargs,
        )
