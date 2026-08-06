#!/usr/bin/env python3
"""Locate and probe theme-generation requests without rerunning network/LDA stages.

Examples:
  python scripts/theme_isolation_probe.py \
    --config configs/twitter/retweet_quote_evolution.yml \
    --input-hash 7eeafc6e5662

  python scripts/theme_isolation_probe.py \
    --config configs/twitter/retweet_quote_evolution.yml \
    --input-hash 7eeafc6e5662 --live --ignore-cache

  python scripts/theme_isolation_probe.py \
    --config configs/twitter/retweet_quote_evolution.yml \
    --preflight --output .cache/theme_preflight.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.config.loader import load_config
from src.providers.base import build_theme_request
from src.providers.factory import build_theme_provider
from src.themes.theme_generation import extract_unique_keywords


@dataclass(frozen=True)
class SourceOccurrence:
    month: str
    file: str
    row_index: int
    keyword_kind: str
    absolute_community: Any
    weighted_community: Any


@dataclass
class PayloadRecord:
    input_hash: str
    keywords: list[str]
    sources: list[SourceOccurrence]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Locate a theme request by input hash, probe exactly one live request, "
            "or preflight all saved theme inputs without rerunning network/LDA."
        )
    )
    parser.add_argument("--config", required=True, help="Merged project config path")
    parser.add_argument(
        "--run-root",
        help="Exact run directory. Defaults to the newest run below output_base_path/runs.",
    )
    parser.add_argument(
        "--input-hash",
        help="Full or prefix input hash from provider diagnostics, e.g. 7eeafc6e5662.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the configured live provider for the matching payload only.",
    )
    parser.add_argument(
        "--ignore-cache",
        action="store_true",
        help="Disable theme cache for a live single-payload probe.",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Process every unique saved payload sequentially, recording failures and continuing.",
    )
    parser.add_argument(
        "--output",
        default=".cache/theme_preflight.jsonl",
        help="JSONL report path for --preflight.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of unique payloads for --preflight.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help=(
            "Repeat one live probe this many times. Use with --ignore-cache to "
            "exercise the deployment guardrail on every attempt."
        ),
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.0,
        help="Delay between repeated live probes.",
    )
    parser.add_argument(
        "--sdk-debug",
        action="store_true",
        help=(
            "Enable OpenAI/httpx wire logs. These can contain raw prompts; leave "
            "disabled for normal research diagnostics."
        ),
    )
    return parser.parse_args()


def newest_run(output_base_path: str) -> Path:
    runs_root = Path(output_base_path).expanduser() / "runs"
    runs = [path for path in runs_root.iterdir() if path.is_dir()] if runs_root.exists() else []
    if not runs:
        raise SystemExit(f"No run directories found below {runs_root}")
    return max(runs, key=lambda path: path.stat().st_mtime)


def theme_input_dir(config: dict[str, Any], run_root: Path) -> Path:
    return (
        run_root
        / str(config.get("data_type", "twitter"))
        / "_intermediate"
        / "theme_inputs"
        / str(config.get("content_type", "mixed"))
        / str(config.get("year", "2017"))
    )


def build_payload_inventory(input_dir: Path, year: str) -> dict[str, PayloadRecord]:
    files = sorted(input_dir.glob(f"*_{year}.parquet"))
    if not files:
        raise SystemExit(f"No saved monthly theme-input parquet files found in {input_dir}")

    by_hash: dict[str, PayloadRecord] = {}
    source_map: dict[str, list[SourceOccurrence]] = defaultdict(list)

    for path in files:
        month = path.stem[: -(len(year) + 1)] if path.stem.endswith(f"_{year}") else path.stem
        frame = extract_unique_keywords(pd.read_parquet(path))
        for row_index, row in frame.iterrows():
            for keyword_kind, column in (
                ("absolute", "absolute_keywords"),
                ("weighted", "weighted_keywords"),
                ("general", "all_keywords"),
            ):
                keywords = list(row[column])
                if not keywords:
                    continue
                request = build_theme_request(keywords)
                source_map[request.input_hash].append(
                    SourceOccurrence(
                        month=month,
                        file=str(path),
                        row_index=int(row_index),
                        keyword_kind=keyword_kind,
                        absolute_community=row.get("absolute_community"),
                        weighted_community=row.get("weighted_community"),
                    )
                )
                by_hash.setdefault(
                    request.input_hash,
                    PayloadRecord(
                        input_hash=request.input_hash,
                        keywords=keywords,
                        sources=[],
                    ),
                )

    for input_hash, sources in source_map.items():
        by_hash[input_hash].sources.extend(sources)
    return by_hash


def select_hash(inventory: dict[str, PayloadRecord], prefix: str) -> PayloadRecord:
    matches = [record for key, record in inventory.items() if key.startswith(prefix)]
    if not matches:
        raise SystemExit(f"No payload matched input hash prefix {prefix!r}")
    if len(matches) > 1:
        hashes = ", ".join(record.input_hash for record in matches[:10])
        raise SystemExit(f"Hash prefix is ambiguous; matching hashes: {hashes}")
    return matches[0]


def print_record(record: PayloadRecord) -> None:
    print(json.dumps({
        "input_hash": record.input_hash,
        "keywords": record.keywords,
        "sources": [asdict(source) for source in record.sources],
    }, indent=2, ensure_ascii=False, default=str))


def build_provider(config: dict[str, Any], *, ignore_cache: bool):
    if ignore_cache:
        config = json.loads(json.dumps(config))
        config.setdefault("theme_provider", {})["cache_backend"] = "none"
    return build_theme_provider(config)


def safe_metrics(provider) -> dict[str, Any]:
    metrics = dict(getattr(provider, "run_metrics", {}))
    metrics.pop("prompts_and_responses", None)
    return metrics


def live_probe(
    config: dict[str, Any],
    record: PayloadRecord,
    *,
    ignore_cache: bool,
    repeat: int,
    delay_seconds: float,
) -> int:
    provider = build_provider(config, ignore_cache=ignore_cache)
    total = max(1, repeat)
    failures = 0
    for attempt in range(1, total + 1):
        print(
            f"Calling configured provider attempt={attempt}/{total} "
            f"input_hash={record.input_hash[:12]} ..."
        )
        try:
            result = provider.generate_theme(record.keywords)
        except Exception as exc:  # deliberate diagnostic boundary
            failures += 1
            print(json.dumps({
                "status": "failed",
                "attempt": attempt,
                "input_hash": record.input_hash,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "metrics": safe_metrics(provider),
            }, indent=2, ensure_ascii=False, default=str))
        else:
            print(json.dumps({
                "status": "passed",
                "attempt": attempt,
                "input_hash": record.input_hash,
                "theme_names": list(result),
                "metrics": safe_metrics(provider),
            }, indent=2, ensure_ascii=False, default=str))
        if attempt < total and delay_seconds > 0:
            time.sleep(delay_seconds)
    return 2 if failures else 0


def preflight(
    config: dict[str, Any],
    inventory: dict[str, PayloadRecord],
    *,
    output: Path,
    limit: int | None,
) -> int:
    provider = build_provider(config, ignore_cache=False)
    records = sorted(inventory.values(), key=lambda record: record.input_hash)
    if limit is not None:
        records = records[: max(0, limit)]

    output.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    with output.open("w", encoding="utf-8") as handle:
        total = len(records)
        for index, record in enumerate(records, start=1):
            event: dict[str, Any] = {
                "input_hash": record.input_hash,
                "keywords": record.keywords,
                "sources": [asdict(source) for source in record.sources],
            }
            try:
                result = provider.generate_theme(record.keywords)
                event.update(status="passed", theme_names=list(result))
            except Exception as exc:  # continue to inventory every failure
                failures += 1
                event.update(
                    status="failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            handle.flush()
            metrics = getattr(provider, "run_metrics", {})
            print(
                f"preflight {index}/{total} status={event['status']} "
                f"input_hash={record.input_hash[:12]} "
                f"cache_hits={metrics.get('cache_hits', 0)} "
                f"outbound_requests={metrics.get('outbound_requests', 0)}"
            )

    summary = {
        "status": "failed" if failures else "passed",
        "payloads": len(records),
        "failures": failures,
        "report": str(output),
        "metrics": safe_metrics(provider),
    }
    print(json.dumps(summary, indent=2, default=str))
    return 2 if failures else 0


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if not args.sdk_debug:
        for logger_name in ("openai", "httpx", "httpcore"):
            logging.getLogger(logger_name).setLevel(logging.WARNING)

    if not args.input_hash and not args.preflight:
        raise SystemExit("Provide --input-hash or --preflight")
    if args.live and not args.input_hash:
        raise SystemExit("--live requires --input-hash")

    config = load_config(args.config)
    run_root = Path(args.run_root).expanduser() if args.run_root else newest_run(
        str(config.get("output_base_path", "results/"))
    )
    input_dir = theme_input_dir(config, run_root)
    inventory = build_payload_inventory(input_dir, str(config.get("year", "2017")))
    print(f"run_root={run_root}")
    print(f"theme_input_dir={input_dir}")
    print(f"unique_payloads={len(inventory)}")

    if args.input_hash:
        record = select_hash(inventory, args.input_hash)
        print_record(record)
        if args.live:
            return live_probe(
                config,
                record,
                ignore_cache=args.ignore_cache,
                repeat=args.repeat,
                delay_seconds=max(0.0, args.delay_seconds),
            )

    if args.preflight:
        return preflight(
            config,
            inventory,
            output=Path(args.output),
            limit=args.limit,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
