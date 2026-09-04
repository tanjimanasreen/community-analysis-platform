from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from src.api.errors import ArtifactUnavailableError, InvalidFilterError

if TYPE_CHECKING:
    import pandas as pd
    from src.api.services.artifact_reader import ArtifactReader

_PERIOD_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])$")


class ThemeClusterService:
    """Read-only reporting over saved clustered/canonical theme artifacts."""

    def __init__(self, reader: ArtifactReader):
        self.reader = reader

    def monthly(
        self, run_id: str, *, period: str, scope: str = "matched"
    ) -> dict[str, Any]:
        self._validate_scope(scope, run_id)
        period = _validate_period(period, run_id)
        record = self._monthly_records(run_id).get(period)
        if record is None:
            raise InvalidFilterError(
                f"Period {period} is not available for clustered themes.", run_id=run_id
            )
        frame = self.reader.read_parquet_record(run_id, record)
        return {
            "run_id": run_id,
            "scope": scope,
            "complete": True,
            **_monthly_summary(period, frame),
        }

    def timeline(
        self,
        run_id: str,
        *,
        period_start: str | None = None,
        period_end: str | None = None,
        scope: str = "matched",
    ) -> dict[str, Any]:
        self._validate_scope(scope, run_id)
        if period_start is not None:
            period_start = _validate_period(period_start, run_id)
        if period_end is not None:
            period_end = _validate_period(period_end, run_id)
        if period_start and period_end and period_start > period_end:
            raise InvalidFilterError(
                "period_start must be before or equal to period_end.", run_id=run_id
            )

        records = self._monthly_records(run_id)
        available_periods = sorted(records)
        periods = [
            period
            for period in available_periods
            if (period_start is None or period >= period_start)
            and (period_end is None or period <= period_end)
        ]
        if not periods:
            raise InvalidFilterError(
                "The selected clustered-theme range contains no available periods.",
                run_id=run_id,
            )
        summaries = [
            _monthly_summary(
                period, self.reader.read_parquet_record(run_id, records[period])
            )
            for period in periods
        ]
        return {
            "run_id": run_id,
            "scope": scope,
            "available_periods": available_periods,
            "periods": periods,
            "complete": True,
            "source_observation_count": sum(
                int(item["source_observation_count"]) for item in summaries
            ),
            "excluded_records_missing_general_theme": sum(
                int(item["excluded_records_missing_general_theme"])
                for item in summaries
            ),
            "excluded_records_ambiguous_general_theme_serialization": sum(
                int(item["excluded_records_ambiguous_general_theme_serialization"])
                for item in summaries
            ),
            "monthly_noise_observation_count": sum(
                int(item["monthly_noise_observation_count"]) for item in summaries
            ),
            "distinct_canonical_theme_count": len(
                {
                    theme["theme_id"]
                    for summary in summaries
                    for theme in summary["themes"]
                }
            ),
            "monthly_summaries": summaries,
            "most_discussed_theme": _dominant_theme(summaries),
        }

    def evidence(
        self,
        run_id: str,
        *,
        period: str,
        canonical_theme_id: str,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        period = _validate_period(period, run_id)
        normalized_id = str(canonical_theme_id or "").strip()
        if not normalized_id:
            raise InvalidFilterError("canonical_theme_id is required.", run_id=run_id)
        record = self._evidence_records(run_id).get(period)
        if record is None:
            raise InvalidFilterError(
                f"Period {period} is not available for clustered-theme evidence.",
                run_id=run_id,
            )
        frame = self.reader.read_parquet_record(run_id, record)
        if "canonical_theme_id" not in frame.columns:
            raise ArtifactUnavailableError(run_id, record.key)
        frame = frame[frame["canonical_theme_id"].astype(str) == normalized_id]
        total = len(frame)
        page = frame.iloc[offset : offset + limit]
        records = []
        for row in page.to_dict(orient="records"):
            records.append(
                {
                    "period": _text(row.get("period")),
                    "canonical_theme_id": _nullable_text(row.get("canonical_theme_id")),
                    "canonical_theme_label": _nullable_text(
                        row.get("canonical_theme_label")
                    ),
                    "monthly_cluster_id": _nullable_text(row.get("monthly_cluster_id")),
                    "monthly_representative_theme": _nullable_text(
                        row.get("monthly_representative_theme")
                    ),
                    "source_general_theme_label": _text(
                        row.get("source_general_theme_label")
                    ),
                    "absolute_community": _nullable_text(row.get("absolute_community")),
                    "weighted_community": _nullable_text(row.get("weighted_community")),
                    "keywords": _text_list(row.get("general_keywords")),
                    "membership_probability": _float(row.get("membership_probability")),
                }
            )
        return {
            "run_id": run_id,
            "period": period,
            "canonical_theme_id": normalized_id,
            "records": records,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _monthly_records(self, run_id: str) -> dict[str, Any]:
        records = self.reader.find_records(run_id, key_prefix="theme_clusters_")
        if not records:
            raise ArtifactUnavailableError(run_id, "theme_clusters_*")
        result: dict[str, Any] = {}
        for record in records:
            match = re.search(r"theme_clusters_(\d{4}-\d{2})$", record.key)
            if match:
                result[match.group(1)] = record
        if not result:
            raise ArtifactUnavailableError(run_id, "theme_clusters_*")
        return result

    def _evidence_records(self, run_id: str) -> dict[str, Any]:
        records = self.reader.find_records(
            run_id, key_prefix="theme_cluster_observations_"
        )
        if not records:
            raise ArtifactUnavailableError(run_id, "theme_cluster_observations_*")
        result: dict[str, Any] = {}
        for record in records:
            match = re.search(r"theme_cluster_observations_(\d{4}-\d{2})$", record.key)
            if match:
                result[match.group(1)] = record
        return result

    @staticmethod
    def _validate_scope(scope: str, run_id: str) -> None:
        if scope != "matched":
            raise InvalidFilterError(
                "Clustered themes currently support only scope=matched.", run_id=run_id
            )


def _monthly_summary(period: str, frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "period": period,
            "source_observation_count": 0,
            "excluded_records_missing_general_theme": 0,
            "excluded_records_ambiguous_general_theme_serialization": 0,
            "monthly_noise_observation_count": 0,
            "total_themed_community_pairs": 0,
            "distinct_clustered_theme_count": 0,
            "themes": [],
            "embedding_provider": None,
            "embedding_model": None,
            "monthly_cluster_contract_version": None,
            "canonicalization_contract_version": None,
        }
    rows = frame.to_dict(orient="records")
    first = rows[0]
    themes = []
    for row in rows:
        theme_id = _text(row.get("canonical_theme_id"))
        if not theme_id:
            continue
        themes.append(
            {
                "theme_id": theme_id,
                "name": _text(row.get("canonical_theme_label")),
                "community_count": int(row.get("community_count") or 0),
                "percentage": float(row.get("percentage") or 0.0),
                "keywords": _text_list(row.get("prominent_keywords"))[:20],
                "monthly_cluster_ids": _text_list(row.get("monthly_cluster_ids")),
                "monthly_representative_themes": _text_list(
                    row.get("monthly_representative_themes")
                ),
                "source_theme_labels": _text_list(
                    row.get("source_general_theme_labels")
                ),
                "community_pairs": _community_pairs(row.get("community_pairs")),
                "mean_membership_probability": _float(
                    row.get("mean_membership_probability")
                ),
            }
        )
    themes.sort(
        key=lambda item: (
            -item["community_count"],
            item["name"].casefold(),
            item["theme_id"],
        )
    )
    return {
        "period": period,
        "source_observation_count": _max_int(rows, "source_observation_count"),
        "excluded_records_missing_general_theme": _max_int(
            rows, "excluded_records_missing_general_theme"
        ),
        "excluded_records_ambiguous_general_theme_serialization": _max_int(
            rows, "excluded_records_ambiguous_general_theme_serialization"
        ),
        "monthly_noise_observation_count": _max_int(
            rows, "monthly_noise_observation_count"
        ),
        "total_themed_community_pairs": _max_int(rows, "total_themed_community_pairs"),
        "distinct_clustered_theme_count": len(themes),
        "themes": themes,
        "embedding_provider": _nullable_text(first.get("embedding_provider")),
        "embedding_model": _nullable_text(first.get("embedding_model")),
        "monthly_cluster_contract_version": _nullable_text(
            first.get("monthly_cluster_contract_version")
        ),
        "canonicalization_contract_version": _nullable_text(
            first.get("canonicalization_contract_version")
        ),
    }


def _dominant_theme(summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    stats: dict[str, dict[str, Any]] = {}
    keyword_support: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    keyword_display: dict[str, dict[str, str]] = defaultdict(dict)
    for summary in summaries:
        period = str(summary["period"])
        denominator = int(summary["total_themed_community_pairs"])
        for theme in summary["themes"]:
            theme_id = str(theme["theme_id"])
            item = stats.setdefault(
                theme_id,
                {
                    "theme_id": theme_id,
                    "name": str(theme["name"]),
                    "total_community_month_count": 0,
                    "months_present": 0,
                    "peak_period": period,
                    "peak_month_count": -1,
                    "series": [],
                },
            )
            count = int(theme["community_count"])
            item["total_community_month_count"] += count
            item["months_present"] += 1
            if count > item["peak_month_count"] or (
                count == item["peak_month_count"] and period < item["peak_period"]
            ):
                item["peak_period"] = period
                item["peak_month_count"] = count
            item["series"].append(
                {
                    "period": period,
                    "community_count": count,
                    "total_themed_community_pairs": denominator,
                    "percentage": (
                        round((count * 100.0) / denominator, 6) if denominator else 0.0
                    ),
                }
            )
            for pair in theme.get("community_pairs", []):
                pair_id = f"{period}|if:{pair.get('absolute_community') or ''}|wif:{pair.get('weighted_community') or ''}"
                for keyword in pair.get("keywords", []):
                    key = str(keyword).casefold()
                    keyword_support[theme_id][key].add(pair_id)
                    keyword_display[theme_id].setdefault(key, str(keyword))
    if not stats:
        return None
    leader = sorted(
        stats.values(),
        key=lambda item: (
            -item["total_community_month_count"],
            -item["months_present"],
            -item["peak_month_count"],
            item["name"].casefold(),
            item["theme_id"],
        ),
    )[0]
    by_period = {point["period"]: point for point in leader["series"]}
    leader["series"] = [
        by_period.get(
            str(summary["period"]),
            {
                "period": str(summary["period"]),
                "community_count": 0,
                "total_themed_community_pairs": int(
                    summary["total_themed_community_pairs"]
                ),
                "percentage": 0.0,
            },
        )
        for summary in summaries
    ]
    leader["keywords"] = [
        keyword_display[leader["theme_id"]][key]
        for key in sorted(
            keyword_support[leader["theme_id"]],
            key=lambda key: (-len(keyword_support[leader["theme_id"]][key]), key),
        )[:8]
    ]
    return leader


def _community_pairs(value: Any) -> list[dict[str, Any]]:
    parsed = _parse(value)
    if not isinstance(parsed, list):
        return []
    result = []
    for item in parsed:
        if not isinstance(item, Mapping):
            continue
        result.append(
            {
                "absolute_community": _nullable_text(item.get("absolute_community")),
                "weighted_community": _nullable_text(item.get("weighted_community")),
                "source_labels": _text_list(item.get("source_labels")),
                "keywords": _text_list(item.get("keywords")),
            }
        )
    return result


def _parse(value: Any) -> Any:
    if isinstance(value, (list, tuple, Mapping)):
        return value
    import sys

    pd = sys.modules.get("pandas")
    if pd is not None:
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
    elif isinstance(value, float) and value != value:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text and text[0] in "[{(" and text[-1] in "]})":
            for parser in (json.loads, ast.literal_eval):
                try:
                    return parser(text)
                except (json.JSONDecodeError, SyntaxError, ValueError):
                    continue
    return value


def _text_list(value: Any) -> list[str]:
    parsed = _parse(value)
    values = (
        parsed
        if isinstance(parsed, (list, tuple, set))
        else ([] if parsed is None else [parsed])
    )
    result = []
    for item in values:
        text = _text(item)
        if text:
            result.append(text)
    return result


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _nullable_text(value: Any) -> str | None:
    parsed = _parse(value)
    if parsed is None:
        return None
    text = _text(parsed)
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text or None


def _float(value: Any) -> float | None:
    if value is None:
        return None
    import sys

    pd = sys.modules.get("pandas")
    if pd is not None:
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
    elif isinstance(value, float) and value != value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _max_int(rows: list[dict[str, Any]], key: str) -> int:
    values = []
    for row in rows:
        try:
            values.append(int(row.get(key) or 0))
        except (TypeError, ValueError):
            pass
    return max(values, default=0)


def _validate_period(period: str, run_id: str) -> str:
    normalized = _text(period)
    if _PERIOD_RE.fullmatch(normalized) is None:
        raise InvalidFilterError("The period must use YYYY-MM format.", run_id=run_id)
    return normalized
