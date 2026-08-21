from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path

from src.reporting.output_contract import VerificationResult, build_contract_summary


def collect_artifacts(roots: Iterable[str]) -> list[Path]:
    artifacts: list[Path] = []
    for root in roots:
        path = Path(root)
        if path.is_file():
            artifacts.append(path)
        elif path.is_dir():
            artifacts.extend(item for item in path.rglob("*") if item.is_file())
    return sorted(artifacts, key=lambda item: str(item))


def build_artifact_index(
    config: Mapping,
    out_path: str,
    verification_result: VerificationResult | None = None,
) -> Path:
    roots = _artifact_roots(config)
    artifacts = collect_artifacts(roots)
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Community Analysis Artifact Index",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Roots",
        "",
    ]
    lines.extend(f"- `{root}`" for root in roots)
    lines.extend(["", "## Artifacts", ""])
    if artifacts:
        lines.extend(f"- `{artifact}`" for artifact in artifacts)
    else:
        lines.append("- No artifacts found yet.")
    lines.extend(["", "## Contract Verification", ""])
    lines.extend(f"- {line}" for line in build_contract_summary(verification_result))

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def _artifact_roots(config: Mapping) -> list[str]:
    roots = [str(config.get("output_base_path", "results/"))]
    theme = config.get("theme", {})
    if isinstance(theme, Mapping) and theme.get("output_dir"):
        roots.append(str(theme["output_dir"]))
    roots.append("/tmp/community-analysis-sample-interactions.parquet")
    return roots
