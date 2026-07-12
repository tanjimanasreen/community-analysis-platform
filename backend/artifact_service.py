from __future__ import annotations

import ast
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

from src.config.loader import load_config
from src.reporting.output_contract import (
    ArtifactCheck,
    OutputContractError,
    get_output_contract_months,
    get_output_contract_params,
    get_public_artifact_checks,
    verify_output_contract,
)


DEFAULT_CONFIG_PATHS = [
    "configs/sample_twitter_reply.yml",
    "configs/longitudinal/sample_twitter_reply_04.yml",
]
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000


class ArtifactServiceError(ValueError):
    status_code = 400


class RunNotFoundError(ArtifactServiceError):
    status_code = 404


class ArtifactNotFoundError(ArtifactServiceError):
    status_code = 404


class InvalidRequestError(ArtifactServiceError):
    status_code = 422


@dataclass(frozen=True)
class ConfiguredRun:
    run_id: str
    config: Mapping[str, Any]
    config_path: Path | None = None
    longitudinal: bool = False


class ArtifactService:
    def __init__(
        self,
        *,
        config_paths: Iterable[str | Path] | None = None,
        configs: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None = None,
    ):
        self.runs = self._load_runs(config_paths=config_paths, configs=configs)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "read_only": True,
            "configured_runs": len(self.runs),
        }

    def list_runs(self) -> list[dict[str, Any]]:
        return [self._run_metadata(run) for run in self.runs.values()]

    def facets(self, run_id: str) -> dict[str, list[str]]:
        run = self.get_run(run_id)
        config = run.config
        months = self._months_for_run(run)
        return {
            "data_types": [str(config.get("data_type", "twitter"))],
            "content_types": [str(config.get("content_type", "reply"))],
            "years": [str(config.get("year", "2017"))],
            "months": months,
        }

    def verification(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        try:
            result = verify_output_contract(run.config, longitudinal=run.longitudinal)
        except OutputContractError as exc:
            return {
                "ok": False,
                "checked_count": 0,
                "skipped_optional_count": 0,
                "error": str(exc),
            }
        return {
            "ok": True,
            "checked_count": result.checked_count,
            "skipped_optional_count": len(result.skipped_optional),
            "error": None,
        }

    def artifacts(self, run_id: str) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        return [self._artifact_metadata(run, check) for check in self._artifact_checks_for_run(run)]

    def community_summary(self, run_id: str, month: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        month = self._validate_month(run, month)
        paths = self._paths(run)
        content = paths["content_type"]
        return {
            "month": month,
            "matched_summary": self._first_record(paths["base"] / "communities" / "matched" / content / f"{month}.csv", "matched_communities"),
            "user_message_counts": self._first_record(paths["base"] / "count_user_messages" / content / f"{month}.csv", "count_user_messages"),
            "daily_message_stats": self._first_record(paths["base"] / "daily_messages_stat" / content / f"{month}.csv", "daily_messages_stat"),
            "user_centrality": self._first_record(paths["base"] / "user_centrality" / content / f"{month}.csv", "user_centrality"),
        }

    def communities(self, run_id: str, month: str, match_type: str, limit: int, offset: int) -> dict[str, Any]:
        run = self.get_run(run_id)
        month = self._validate_month(run, month)
        limit, offset = _normalize_pagination(limit, offset)
        paths = self._paths(run)
        content = paths["content_type"]
        if match_type == "matched":
            return self._table(paths["base"] / "communities" / "matched" / content / f"{month}.csv", "matched_communities", limit, offset)
        if match_type == "partial":
            return self._table(
                paths["base"] / "communities" / "partially_matched" / content / f"{month}.csv",
                "partial_matched_communities",
                limit,
                offset,
                required=False,
            )
        raise InvalidRequestError("match_type must be 'matched' or 'partial'")

    def topics(self, run_id: str, month: str, topic_type: str, limit: int, offset: int) -> dict[str, Any]:
        run = self.get_run(run_id)
        month = self._validate_month(run, month)
        limit, offset = _normalize_pagination(limit, offset)
        paths = self._paths(run)
        content = paths["content_type"]
        if topic_type == "matched":
            path = paths["base"] / "LDA" / "matched" / content / f"{month}_{paths['year']}.csv"
            return self._table(path, "matched_lda", limit, offset)
        if topic_type == "partial":
            path = paths["base"] / "LDA" / "partial_matched" / content / f"{month}_{paths['year']}.csv"
            return self._table(path, "partial_matched_lda", limit, offset, required=False)
        if topic_type == "scores":
            return self._table(paths["base"] / "LDA" / "scores" / content / f"{month}.csv", "lda_scores", limit, offset)
        raise InvalidRequestError("type must be 'matched', 'partial', or 'scores'")

    def themes(self, run_id: str, month: str, limit: int, offset: int) -> dict[str, Any]:
        run = self.get_run(run_id)
        month = self._validate_month(run, month)
        limit, offset = _normalize_pagination(limit, offset)
        paths = self._paths(run)
        path = paths["theme_output"] / f"{month}_{paths['year']}_with_themes.csv"
        return self._table(path, "themed_output", limit, offset)

    def transitions(self, run_id: str, limit: int, offset: int) -> dict[str, Any]:
        run = self.get_run(run_id)
        limit, offset = _normalize_pagination(limit, offset)
        paths = self._paths(run)
        return self._table(paths["theme_output"] / "community_transition.csv", "community_transition", limit, offset)

    def files(self, run_id: str) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        paths = self._paths(run)
        files: list[dict[str, Any]] = []
        for category in ["sankey", "membership_changes", "theme_similarity"]:
            root = paths["theme_output"] / category
            if not root.exists():
                files.append(self._file_metadata(run, root, category, exists=False))
                continue
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                files.append(self._file_metadata(run, path, category, exists=True))
        return files

    def get_run(self, run_id: str) -> ConfiguredRun:
        try:
            return self.runs[run_id]
        except KeyError as exc:
            raise RunNotFoundError(f"Unknown run_id: {run_id}") from exc

    def _load_runs(
        self,
        *,
        config_paths: Iterable[str | Path] | None,
        configs: Mapping[str, Mapping[str, Any]] | Iterable[Mapping[str, Any]] | None,
    ) -> dict[str, ConfiguredRun]:
        loaded: list[ConfiguredRun] = []
        if configs is not None:
            if isinstance(configs, Mapping):
                for run_id, config in configs.items():
                    loaded.append(
                        ConfiguredRun(
                            run_id=str(run_id),
                            config=config,
                            longitudinal=_detect_longitudinal(config),
                        )
                    )
            else:
                for index, config in enumerate(configs, start=1):
                    loaded.append(
                        ConfiguredRun(
                            run_id=f"run_{index}",
                            config=config,
                            longitudinal=_detect_longitudinal(config),
                        )
                    )
        else:
            is_default = config_paths is None and not os.environ.get("COMMUNITY_ANALYSIS_API_CONFIGS")
            paths = list(config_paths or _config_paths_from_env())
            for path in paths:
                config_path = Path(path)
                try:
                    config = load_config(config_path)
                except FileNotFoundError:
                    if is_default:
                        continue
                    raise
                loaded.append(
                    ConfiguredRun(
                        run_id=_run_id_from_path(config_path),
                        config=config,
                        config_path=config_path,
                        longitudinal=_detect_longitudinal(config, config_path),
                    )
                )

        runs: dict[str, ConfiguredRun] = {}
        for run in loaded:
            run_id = _unique_run_id(run.run_id, runs)
            runs[run_id] = ConfiguredRun(
                run_id=run_id,
                config=run.config,
                config_path=run.config_path,
                longitudinal=run.longitudinal,
            )
        return runs

    def _run_metadata(self, run: ConfiguredRun) -> dict[str, Any]:
        params = get_output_contract_params(run.config)
        return {
            "run_id": run.run_id,
            "config_path": _redacted_root(str(run.config_path)) if run.config_path else None,
            "data_type": params["data_type"],
            "content_type": params["content_type"],
            "year": params["year"],
            "output_base_path": _redacted_root(params["output_base_path"]),
            "theme_output_dir": _redacted_root(params["theme_output_dir"]),
            "longitudinal": run.longitudinal,
        }

    def _months_for_run(self, run: ConfiguredRun) -> list[str]:
        try:
            return get_output_contract_months(run.config, longitudinal=run.longitudinal)
        except OutputContractError:
            return [str(run.config.get("month", "03"))]

    def _validate_month(self, run: ConfiguredRun, month: str) -> str:
        month = str(month)
        months = self._months_for_run(run)
        if month not in months:
            raise InvalidRequestError(f"Month {month!r} is not available for run {run.run_id!r}; available months: {months}")
        return month

    def _paths(self, run: ConfiguredRun) -> dict[str, Any]:
        params = get_output_contract_params(run.config)
        return {
            "output_base": Path(params["output_base_path"]),
            "base": Path(params["output_base_path"]) / params["data_type"],
            "theme_output": Path(params["theme_output_dir"]),
            "data_type": params["data_type"],
            "content_type": params["content_type"],
            "month": params["month"],
            "year": params["year"],
        }

    def _artifact_checks_for_run(self, run: ConfiguredRun) -> list[ArtifactCheck]:
        try:
            checks = list(get_public_artifact_checks(run.config, longitudinal=run.longitudinal))
        except OutputContractError:
            checks = list(get_public_artifact_checks(run.config, longitudinal=False))
        checks.extend(self._internal_artifact_checks(run))
        checks.extend(self._optional_file_checks(run))
        return checks

    def _internal_artifact_checks(self, run: ConfiguredRun) -> list[ArtifactCheck]:
        paths = self._paths(run)
        months = self._months_for_run(run)
        checks: list[ArtifactCheck] = []
        for month in months:
            topic_dir = (
                paths["base"]
                / "_intermediate"
                / "topic_inputs"
                / paths["content_type"]
                / f"{month}_{paths['year']}"
            )
            for filename in [
                "absolute_community_messages.csv",
                "weighted_community_messages.csv",
                "matched_communities.csv",
                "partial_matched_communities.csv",
                "manifest.json",
            ]:
                checks.append(ArtifactCheck(f"topic_inputs/{filename}", topic_dir / filename, required_columns=None))
            theme_dir = paths["base"] / "_intermediate" / "theme_inputs" / paths["content_type"] / paths["year"]
            checks.append(ArtifactCheck("theme_inputs/month_csv", theme_dir / f"{month}_{paths['year']}.csv", required_columns=None))
        theme_manifest = paths["base"] / "_intermediate" / "theme_inputs" / paths["content_type"] / paths["year"] / "manifest.json"
        checks.append(ArtifactCheck("theme_inputs/manifest.json", theme_manifest, required_columns=None))
        return checks

    def _optional_file_checks(self, run: ConfiguredRun) -> list[ArtifactCheck]:
        paths = self._paths(run)
        checks: list[ArtifactCheck] = []
        for category in ["sankey", "membership_changes", "theme_similarity"]:
            root = paths["theme_output"] / category
            if root.exists():
                for path in sorted(item for item in root.rglob("*") if item.is_file()):
                    checks.append(ArtifactCheck(f"file/{category}", path, required_columns=None, required=False))
            else:
                checks.append(ArtifactCheck(f"file/{category}", root, required_columns=None, required=False))
        return checks

    def _artifact_metadata(self, run: ConfiguredRun, check: ArtifactCheck) -> dict[str, Any]:
        exists = check.path.exists()
        stat = check.path.stat() if exists and check.path.is_file() else None
        return {
            "name": check.name,
            "classification": _classification(check.name),
            "relative_path": self._relative_path(run, check.path),
            "exists": exists,
            "required": check.required,
            "size_bytes": stat.st_size if stat else None,
            "modified_time": _mtime(stat.st_mtime) if stat else None,
            "required_columns": check.required_columns or [],
        }

    def _file_metadata(self, run: ConfiguredRun, path: Path, category: str, *, exists: bool) -> dict[str, Any]:
        stat = path.stat() if exists and path.is_file() else None
        return {
            "category": category,
            "relative_path": self._relative_path(run, path),
            "exists": exists,
            "size_bytes": stat.st_size if stat else None,
            "modified_time": _mtime(stat.st_mtime) if stat else None,
        }

    def _relative_path(self, run: ConfiguredRun, path: Path) -> str:
        paths = self._paths(run)
        resolved = path.resolve()
        roots = [
            ("output", paths["output_base"].resolve()),
            ("theme", paths["theme_output"].resolve()),
        ]
        for label, root in roots:
            try:
                return f"{label}/{resolved.relative_to(root)}"
            except ValueError:
                continue
        return path.name

    def _first_record(self, path: Path, artifact_name: str) -> dict[str, Any]:
        table = self._table(path, artifact_name, limit=1, offset=0)
        return table["records"][0] if table["records"] else {}

    def _table(
        self,
        path: Path,
        artifact_name: str,
        limit: int,
        offset: int,
        *,
        required: bool = True,
    ) -> dict[str, Any]:
        if not path.exists():
            if required:
                raise ArtifactNotFoundError(f"Missing required artifact {artifact_name}: {path.name}")
            return {
                "records": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "missing": True,
                "artifact": artifact_name,
            }
        frame = pd.read_csv(path, low_memory=False)
        total = len(frame)
        sliced = frame.iloc[offset : offset + limit]
        return {
            "records": normalize_records(sliced.to_dict(orient="records")),
            "total": total,
            "limit": limit,
            "offset": offset,
            "missing": False,
            "artifact": artifact_name,
        }


def normalize_records(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{str(key): normalize_value(value) for key, value in record.items()} for record in records]


def normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if value is pd.NaT:
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except ValueError:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if not isinstance(value, (list, tuple, dict, str)) and pd.isna(value):
        return None
    if isinstance(value, str):
        text = value.strip()
        if text == "" or text.lower() in {"nan", "nat", "none", "null"}:
            return None
        if (text.startswith("[") and text.endswith("]")) or (text.startswith("{") and text.endswith("}")):
            try:
                return normalize_value(json.loads(text))
            except json.JSONDecodeError:
                try:
                    return normalize_value(ast.literal_eval(text))
                except (SyntaxError, ValueError):
                    return value
        return value
    if isinstance(value, dict):
        return {str(key): normalize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]
    return value


def _normalize_pagination(limit: int, offset: int) -> tuple[int, int]:
    try:
        limit = int(limit)
        offset = int(offset)
    except (TypeError, ValueError) as exc:
        raise InvalidRequestError("limit and offset must be integers") from exc
    if limit < 1 or limit > MAX_LIMIT:
        raise InvalidRequestError(f"limit must be between 1 and {MAX_LIMIT}")
    if offset < 0:
        raise InvalidRequestError("offset must be greater than or equal to 0")
    return limit, offset


def _config_paths_from_env() -> list[str]:
    raw = os.environ.get("COMMUNITY_ANALYSIS_API_CONFIGS")
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return DEFAULT_CONFIG_PATHS


def _run_id_from_path(path: Path) -> str:
    return path.stem.replace(" ", "_").replace("-", "_")


def _unique_run_id(run_id: str, existing: Mapping[str, ConfiguredRun]) -> str:
    if run_id not in existing:
        return run_id
    index = 2
    while f"{run_id}_{index}" in existing:
        index += 1
    return f"{run_id}_{index}"


def _detect_longitudinal(config: Mapping[str, Any], config_path: Path | None = None) -> bool:
    api_config = config.get("api", {})
    if isinstance(api_config, Mapping) and "longitudinal" in api_config:
        return bool(api_config["longitudinal"])
    if config_path and "longitudinal" in str(config_path):
        return True
    params = get_output_contract_params(config)
    manifest = (
        Path(params["output_base_path"])
        / params["data_type"]
        / "_intermediate"
        / "theme_inputs"
        / params["content_type"]
        / params["year"]
        / "manifest.json"
    )
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False
        return len(data.get("months", [])) > 1
    return False


def _redacted_root(path: str) -> str:
    return Path(path).name or path


def _mtime(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _classification(name: str) -> str:
    if name.startswith("topic_inputs") or name.startswith("theme_inputs"):
        return "internal"
    if name.startswith("file/"):
        return "optional"
    return "public"
