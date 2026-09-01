from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Mapping


def embedding_dimensions(
    base_url: str,
    api_key: str | None,
    *,
    timeout: float = 5.0,
    normalize: bool = True,
) -> int:
    """Execute one lightweight TEI embedding request and return vector width."""
    payload = json.dumps(
        {"inputs": ["community analysis health check"], "normalize": normalize}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/embed",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    if isinstance(body, dict) and "embeddings" in body:
        body = body["embeddings"]
    if isinstance(body, dict) and "data" in body:
        body = [item["embedding"] for item in body["data"]]
    if (
        not isinstance(body, list)
        or len(body) != 1
        or not isinstance(body[0], list)
        or not body[0]
    ):
        raise RuntimeError("TEI returned an invalid embedding payload")
    return len(body[0])


def wait_for_tei_services(
    config: Mapping[str, Any] | None = None,
    *,
    attempts: int = 30,
    interval: float = 1.0,
    timeout: float = 5.0,
) -> dict[str, int]:
    """Poll configured TEI services for readiness with bounded retries.

    Independently checks similarity and clustering profiles if their
    resolved provider is set to 'tei'. If neither is 'tei', returns {}.
    Raises RuntimeError on timeout or health check error (fails closed).
    """
    from src.config.settings import (
        get_clustering_settings,
        get_clustering_tei_client_settings,
        get_similarity_settings,
        get_tei_client_settings,
    )

    theme = (config or {}).get("theme", {})
    theme = theme if isinstance(theme, Mapping) else {}

    services_to_check: list[tuple[str, str, str | None, bool]] = []

    # Check similarity profile if configured
    sim_runtime = get_similarity_settings()
    sim_provider = (
        str(theme.get("similarity_provider", sim_runtime.provider)).strip().lower()
    )
    if sim_provider == "tei":
        sim_settings = get_tei_client_settings()
        sim_api_key = (
            sim_settings.api_key.get_secret_value() if sim_settings.api_key else None
        )
        services_to_check.append(
            ("similarity", str(sim_settings.base_url).rstrip("/"), sim_api_key, True)
        )

    # Check clustering profile if configured
    clust_runtime = get_clustering_settings()
    clust_provider = (
        str(theme.get("clustering_provider", clust_runtime.provider)).strip().lower()
    )
    if clust_provider == "tei":
        clust_settings = get_clustering_tei_client_settings()
        clust_api_key = (
            clust_settings.api_key.get_secret_value()
            if clust_settings.api_key
            else None
        )
        services_to_check.append(
            (
                "clustering",
                str(clust_settings.base_url).rstrip("/"),
                clust_api_key,
                False,
            )
        )

    if not services_to_check:
        return {}

    results: dict[str, int] = {}
    for profile, base_url, api_key, normalize in services_to_check:
        ready = False
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                dims = embedding_dimensions(
                    base_url=base_url,
                    api_key=api_key,
                    timeout=timeout,
                    normalize=normalize,
                )
                if dims != 384:
                    raise RuntimeError(
                        f"TEI {profile} service at {base_url} returned dimension {dims}, expected 384."
                    )
                results[profile] = dims
                ready = True
                break
            except RuntimeError as rerr:
                if "expected 384" in str(rerr):
                    raise
                last_error = rerr
                if attempt < attempts:
                    time.sleep(interval)
            except Exception as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(interval)
        if not ready:
            raise RuntimeError(
                f"TEI {profile} service at {base_url} failed readiness check after {attempts} attempts. "
                f"Last error: {last_error}"
            )

    return results
