from __future__ import annotations

import argparse
import time
import urllib.error


def _embed(base_url: str, api_key: str | None, timeout: float) -> int:
    from src.themes.tei_health import embedding_dimensions

    return embedding_dimensions(base_url, api_key, timeout=timeout, normalize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check both project TEI embedding profiles.")
    parser.add_argument("--wait", action="store_true", help="retry while services are starting")
    parser.add_argument("--attempts", type=int, default=30)
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    from src.config.settings import (
        get_clustering_tei_client_settings,
        get_tei_client_settings,
    )

    similarity = get_tei_client_settings()
    clustering = get_clustering_tei_client_settings()
    profiles = [
        (
            "similarity",
            str(similarity.base_url).rstrip("/"),
            similarity.api_key.get_secret_value() if similarity.api_key else None,
            similarity.model_id,
            similarity.revision,
        ),
        (
            "clustering",
            str(clustering.base_url).rstrip("/"),
            clustering.api_key.get_secret_value() if clustering.api_key else None,
            clustering.model_id,
            clustering.revision,
        ),
    ]

    failures: list[str] = []
    for name, base_url, api_key, model, revision in profiles:
        attempts = args.attempts if args.wait else 1
        error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                dimensions = _embed(base_url, api_key, timeout=5.0)
                print(f"{name}: healthy endpoint={base_url} model={model} revision={revision} dimensions={dimensions}")
                error = None
                break
            except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
                error = exc
                if attempt < attempts:
                    time.sleep(args.interval)
        if error is not None:
            failures.append(f"{name}: {error}")

    if failures:
        for failure in failures:
            print(f"ERROR {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
