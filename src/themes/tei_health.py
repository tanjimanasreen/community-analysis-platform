from __future__ import annotations

import json
import urllib.request


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
