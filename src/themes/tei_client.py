from __future__ import annotations

from typing import List, Union

import numpy as np
import requests


class TEIClient:
    """Small connection-reusing client for Hugging Face TEI embeddings."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        api_key: str | None = None,
        client_batch_size: int = 32,
        timeout_seconds: float = 60.0,
        session: requests.Session | None = None,
        normalize: bool = True,
    ):
        self.base_url = base_url.rstrip("/")
        self.embed_endpoint = f"{self.base_url}/embed"
        self.predict_endpoint = f"{self.base_url}/predict"
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self.client_batch_size = max(1, int(client_batch_size))
        self.timeout_seconds = float(timeout_seconds)
        self.normalize = bool(normalize)
        self._session = session or requests.Session()

    def _post(self, endpoint: str, payload: dict):
        return self._session.post(
            endpoint,
            json=payload,
            headers=self.headers,
            timeout=self.timeout_seconds,
        )

    @staticmethod
    def _parse_embeddings(payload) -> list:
        if isinstance(payload, dict) and "embeddings" in payload:
            return list(payload["embeddings"])
        if isinstance(payload, dict) and "data" in payload:
            return [item["embedding"] for item in payload["data"]]
        if isinstance(payload, list):
            return payload
        raise RuntimeError("TEI returned an unsupported embedding response shape")

    def encode(self, sentences: Union[str, List[str]]) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]
        if not sentences:
            return np.empty((0, 0), dtype=float)

        all_embeddings: list = []
        for start in range(0, len(sentences), self.client_batch_size):
            batch = sentences[start : start + self.client_batch_size]
            payload = {"inputs": batch, "normalize": self.normalize}
            response = self._post(self.embed_endpoint, payload)
            if response.status_code == 404:
                response = self._post(self.predict_endpoint, payload)
            if response.status_code != 200:
                body = response.text[:1000]
                raise RuntimeError(
                    f"TEI request failed with status {response.status_code}: {body}"
                )
            embeddings = self._parse_embeddings(response.json())
            if len(embeddings) != len(batch):
                raise RuntimeError(
                    "TEI embedding count mismatch: "
                    f"expected {len(batch)}, received {len(embeddings)}"
                )
            all_embeddings.extend(embeddings)

        matrix = np.asarray(all_embeddings, dtype=float)
        if matrix.ndim != 2 or not np.isfinite(matrix).all():
            raise RuntimeError("TEI returned invalid or non-finite embeddings")
        return matrix

    def close(self) -> None:
        self._session.close()
