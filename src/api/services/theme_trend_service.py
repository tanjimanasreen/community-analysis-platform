from __future__ import annotations

import ast
import calendar
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import pandas as pd

from src.api.errors import ArtifactUnavailableError, InvalidFilterError

if TYPE_CHECKING:
    from src.api.services.artifact_reader import ArtifactReader

_PERIOD_RE = re.compile(r"^(?P<year>\d{4})-(?P<month>0[1-9]|1[0-2])$")
_MONTH_NAMES = {
    name.lower(): index for index, name in enumerate(calendar.month_name) if name
}
_MONTH_NAMES.update(
    {name.lower(): index for index, name in enumerate(calendar.month_abbr) if name}
)


@dataclass
class _KeywordEvidence:
    display: str
    source_order: int
    pairs: set[str] = field(default_factory=set)


@dataclass
class _PairEvidence:
    absolute_community: str | None
    weighted_community: str | None
    keywords: list[str] = field(default_factory=list)


@dataclass
class _ThemeAccumulator:
    pairs: set[str] = field(default_factory=set)
    keywords: dict[str, _KeywordEvidence] = field(default_factory=dict)
    pair_evidence: dict[str, _PairEvidence] = field(default_factory=dict)


class ThemeTrendService:
    """Read-only, deterministic aggregations over saved monthly theme artifacts."""

    def __init__(self, reader: ArtifactReader):
        self.reader = reader

    def monthly(
        self, run_id: str, *, period: str, scope: str = "matched"
    ) -> dict[str, Any]:
        self._validate_scope(scope, run_id)
        period = _validate_period(period, run_id)
        artifacts_by_period = self._artifacts_by_period(run_id)
        if period not in artifacts_by_period:
            available = ", ".join(sorted(artifacts_by_period))
            suffix = f" Available periods: {available}." if available else ""
            raise InvalidFilterError(
                f"Period {period} is not available for theme trends.{suffix}",
                run_id=run_id,
            )
        records = self._records_for_artifacts(run_id, artifacts_by_period[period])
        summary = _aggregate_period(period, records)
        return {
            "run_id": run_id,
            "scope": scope,
            "complete": True,
            **summary,
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
                "period_start must be before or equal to period_end.",
                run_id=run_id,
            )

        artifacts_by_period = self._artifacts_by_period(run_id)
        available_periods = sorted(artifacts_by_period)
        periods = [
            period
            for period in available_periods
            if (period_start is None or period >= period_start)
            and (period_end is None or period <= period_end)
        ]
        if not periods:
            raise InvalidFilterError(
                "The selected theme-trend range contains no available periods.",
                run_id=run_id,
            )

        monthly_summaries = [
            _aggregate_period(
                period,
                self._records_for_artifacts(run_id, artifacts_by_period[period]),
            )
            for period in periods
        ]
        leader = _dominant_theme(monthly_summaries)
        return {
            "run_id": run_id,
            "scope": scope,
            "available_periods": available_periods,
            "periods": periods,
            "complete": True,
            "source_record_count": sum(
                int(summary["source_record_count"]) for summary in monthly_summaries
            ),
            "excluded_records_without_pair": sum(
                int(summary["excluded_records_without_pair"])
                for summary in monthly_summaries
            ),
            "monthly_summaries": monthly_summaries,
            "most_discussed_theme": leader,
        }

    def _artifacts_by_period(self, run_id: str) -> dict[str, list[Any]]:
        artifacts = sorted(
            self.reader.find_records(run_id, key_prefix="themes_"),
            key=lambda record: record.key,
        )
        if not artifacts:
            raise ArtifactUnavailableError(run_id, "themes_*")

        fallback_year = _fallback_year(self.reader, run_id, artifacts)
        artifacts_by_period: dict[str, list[Any]] = {}
        for artifact in artifacts:
            period = _artifact_period(artifact, fallback_year=fallback_year)
            if period is not None:
                artifacts_by_period.setdefault(period, []).append(artifact)

        if not artifacts_by_period:
            raise ArtifactUnavailableError(run_id, "themes_*")
        return artifacts_by_period

    def _records_for_artifacts(
        self, run_id: str, artifacts: Iterable[Any]
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for artifact in artifacts:
            frame = self.reader.read_parquet_record(run_id, artifact)
            records.extend(_frame_records(frame))
        return records

    @staticmethod
    def _validate_scope(scope: str, run_id: str) -> None:
        if scope != "matched":
            raise InvalidFilterError(
                "Theme trends currently support only scope=matched.",
                run_id=run_id,
            )


def _aggregate_period(period: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    themes: dict[str, _ThemeAccumulator] = {}
    themed_pairs: set[str] = set()
    excluded_records_without_pair = 0
    keyword_source_order = 0

    for record in records:
        absolute_id = _community_id(record.get("absolute_community"))
        weighted_id = _community_id(record.get("weighted_community"))
        pair_key = _pair_key(absolute_id, weighted_id)
        if pair_key is None:
            excluded_records_without_pair += 1
            continue

        entries = _theme_entries(record)
        if not entries:
            continue
        themed_pairs.add(pair_key)

        for name, keywords in entries:
            accumulator = themes.setdefault(name, _ThemeAccumulator())
            accumulator.pairs.add(pair_key)
            pair = accumulator.pair_evidence.setdefault(
                pair_key,
                _PairEvidence(
                    absolute_community=absolute_id,
                    weighted_community=weighted_id,
                ),
            )
            seen_pair_keywords = {item.casefold() for item in pair.keywords}
            for keyword in keywords:
                normalized = _display_text(keyword)
                if not normalized:
                    continue
                keyword_key = normalized.casefold()
                evidence = accumulator.keywords.get(keyword_key)
                if evidence is None:
                    evidence = _KeywordEvidence(
                        display=normalized,
                        source_order=keyword_source_order,
                    )
                    accumulator.keywords[keyword_key] = evidence
                    keyword_source_order += 1
                evidence.pairs.add(pair_key)
                if keyword_key not in seen_pair_keywords:
                    pair.keywords.append(normalized)
                    seen_pair_keywords.add(keyword_key)

    denominator = len(themed_pairs)
    theme_rows = []
    for name, accumulator in themes.items():
        keywords = sorted(
            accumulator.keywords.values(),
            key=lambda item: (
                -len(item.pairs),
                item.source_order,
                item.display.casefold(),
            ),
        )
        pair_rows = sorted(
            accumulator.pair_evidence.values(),
            key=lambda item: (
                item.absolute_community or "",
                item.weighted_community or "",
            ),
        )
        theme_rows.append(
            {
                "name": name,
                "community_count": len(accumulator.pairs),
                "percentage": (
                    round((len(accumulator.pairs) * 100.0) / denominator, 6)
                    if denominator
                    else 0.0
                ),
                "keywords": [item.display for item in keywords[:5]],
                "community_pairs": [
                    {
                        "absolute_community": item.absolute_community,
                        "weighted_community": item.weighted_community,
                        "keywords": item.keywords[:12],
                    }
                    for item in pair_rows
                ],
            }
        )

    theme_rows.sort(key=lambda item: (-item["community_count"], item["name"]))
    return {
        "period": period,
        "source_record_count": len(records),
        "excluded_records_without_pair": excluded_records_without_pair,
        "total_themed_community_pairs": denominator,
        "distinct_exact_theme_count": len(theme_rows),
        "themes": theme_rows,
    }


def _dominant_theme(monthly_summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    stats: dict[str, dict[str, Any]] = {}
    keyword_pairs: dict[str, dict[str, _KeywordEvidence]] = defaultdict(dict)
    keyword_order = 0

    for summary in monthly_summaries:
        period = str(summary["period"])
        denominator = int(summary["total_themed_community_pairs"])
        for theme in summary["themes"]:
            name = str(theme["name"])
            count = int(theme["community_count"])
            item = stats.setdefault(
                name,
                {
                    "name": name,
                    "total_community_month_count": 0,
                    "months_present": 0,
                    "peak_period": period,
                    "peak_month_count": -1,
                    "series": [],
                },
            )
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
                pair_key = _pair_key(
                    _community_id(pair.get("absolute_community")),
                    _community_id(pair.get("weighted_community")),
                )
                if pair_key is None:
                    continue
                community_month_key = f"{period}|{pair_key}"
                for raw_keyword in pair.get("keywords", []):
                    keyword = _display_text(raw_keyword)
                    if not keyword:
                        continue
                    keyword_key = keyword.casefold()
                    evidence = keyword_pairs[name].get(keyword_key)
                    if evidence is None:
                        evidence = _KeywordEvidence(keyword, keyword_order)
                        keyword_pairs[name][keyword_key] = evidence
                        keyword_order += 1
                    evidence.pairs.add(community_month_key)

    if not stats:
        return None

    ranked = sorted(
        stats.values(),
        key=lambda item: (
            -item["total_community_month_count"],
            -item["months_present"],
            -item["peak_month_count"],
            item["name"],
        ),
    )
    leader = ranked[0]
    periods = [str(summary["period"]) for summary in monthly_summaries]
    by_period = {item["period"]: item for item in leader["series"]}
    leader["series"] = [
        by_period.get(
            period,
            {
                "period": period,
                "community_count": 0,
                "total_themed_community_pairs": int(
                    next(
                        summary["total_themed_community_pairs"]
                        for summary in monthly_summaries
                        if summary["period"] == period
                    )
                ),
                "percentage": 0.0,
            },
        )
        for period in periods
    ]
    leader["keywords"] = [
        item.display
        for item in sorted(
            keyword_pairs[leader["name"]].values(),
            key=lambda item: (
                -len(item.pairs),
                item.source_order,
                item.display.casefold(),
            ),
        )[:8]
    ]
    return leader


def exact_theme_names(record: Mapping[str, Any]) -> list[str]:
    """Return the exact labels used by trend aggregation for one theme row."""
    return [name for name, _keywords in _theme_entries(record)]


def _theme_entries(record: Mapping[str, Any]) -> list[tuple[str, list[str]]]:
    general_names = _text_list(record.get("general_theme_names"))
    general_mapping = _normalized_mapping(record.get("general_theme_gpt"))
    if general_names or general_mapping:
        names = general_names or list(general_mapping)
        explicit_keywords = _text_list(record.get("all_keywords"))
        return [
            (
                name,
                explicit_keywords or _mapping_keywords_for_name(general_mapping, name),
            )
            for name in _unique_exact(names)
        ]

    entries: dict[str, list[str]] = {}
    for prefix in ("absolute", "weighted"):
        names = _text_list(record.get(f"{prefix}_theme_names"))
        mapping = _normalized_mapping(record.get(f"{prefix}_theme_gpt"))
        names = names or list(mapping)
        explicit_keywords = _text_list(record.get(f"{prefix}_keywords"))
        for name in _unique_exact(names):
            keywords = explicit_keywords or _mapping_keywords_for_name(mapping, name)
            entries.setdefault(name, []).extend(keywords)
    return [(name, _unique_exact(values)) for name, values in entries.items() if name]


def _normalized_mapping(value: Any) -> dict[str, Any]:
    normalized = _normalize(value)
    if not isinstance(normalized, Mapping):
        return {}
    result: dict[str, Any] = {}
    for raw_name, raw_keywords in normalized.items():
        name = _display_text(raw_name)
        if name:
            result[name] = raw_keywords
    return result


def _mapping_keywords_for_name(mapping: Mapping[str, Any], name: str) -> list[str]:
    return _text_list(mapping.get(name))


def _text_list(value: Any) -> list[str]:
    normalized = _normalize(value)
    if normalized is None:
        return []
    if isinstance(normalized, Mapping):
        items: Iterable[Any] = normalized.keys()
    elif isinstance(normalized, (list, tuple, set)):
        items = normalized
    else:
        items = [normalized]
    return [text for item in items if (text := _display_text(item))]


def _normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {str(key): _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize(item) for item in value]
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False
    if isinstance(missing, bool) and missing:
        return None
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        try:
            return [_normalize(item) for item in value.tolist()]
        except (TypeError, ValueError, AttributeError):
            pass
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (TypeError, ValueError):
            pass
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and stripped[0] in "[{(" and stripped[-1] in "]})":
            for parser in (json.loads, ast.literal_eval):
                try:
                    return _normalize(parser(stripped))
                except (json.JSONDecodeError, SyntaxError, ValueError):
                    continue
        return value
    return value


def _frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(key): _normalize(value) for key, value in row.items()}
        for row in frame.to_dict(orient="records")
    ]


def _display_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _unique_exact(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _display_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _community_id(value: Any) -> str | None:
    normalized = _normalize(value)
    if normalized is None:
        return None
    if isinstance(normalized, float) and normalized.is_integer():
        return str(int(normalized))
    text = _display_text(normalized)
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text or None


def _pair_key(absolute_id: str | None, weighted_id: str | None) -> str | None:
    if absolute_id is None and weighted_id is None:
        return None
    return f"if:{absolute_id or ''}|wif:{weighted_id or ''}"


def _validate_period(period: str, run_id: str) -> str:
    normalized = _display_text(period)
    if _PERIOD_RE.fullmatch(normalized) is None:
        raise InvalidFilterError(
            "The period must use YYYY-MM format.",
            run_id=run_id,
        )
    return normalized


def _fallback_year(reader: Any, run_id: str, artifacts: list[Any]) -> int | None:
    candidates: list[Any] = []
    try:
        config = reader.read_safe_config(run_id)
        candidates.append(config.get("year"))
        for item in config.get("longitudinal_datasets", []) or []:
            if isinstance(item, Mapping):
                candidates.extend((item.get("year"), item.get("input_path")))
    except Exception:
        pass
    try:
        manifest = reader.catalog.get_manifest(run_id)
        dataset = getattr(manifest, "dataset", {}) or {}
        candidates.extend((dataset.get("date_start"), dataset.get("date_end")))
    except Exception:
        pass
    candidates.extend(getattr(item, "path", "") for item in artifacts)
    for candidate in candidates:
        match = re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", str(candidate or ""))
        if match:
            return int(match.group(1))
    return None


def _artifact_period(artifact: Any, *, fallback_year: int | None) -> str | None:
    key = str(getattr(artifact, "key", ""))
    path = str(getattr(artifact, "path", ""))
    combined = f"{key} {path}"
    direct = re.search(r"(?<!\d)(19\d{2}|20\d{2})[-_/](0[1-9]|1[0-2])(?!\d)", combined)
    if direct:
        return f"{int(direct.group(1)):04d}-{int(direct.group(2)):02d}"
    compact = re.search(r"(?<!\d)(0[1-9]|1[0-2])(19\d{2}|20\d{2})(?!\d)", combined)
    if compact:
        return f"{int(compact.group(2)):04d}-{int(compact.group(1)):02d}"

    month = None
    for token in reversed(re.split(r"[_\-./]", combined.lower())):
        if token.isdigit() and 1 <= int(token) <= 12:
            month = int(token)
            break
        if token in _MONTH_NAMES:
            month = _MONTH_NAMES[token]
            break
    if month is None or fallback_year is None:
        return None
    return f"{fallback_year:04d}-{month:02d}"
