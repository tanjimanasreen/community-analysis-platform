import requests
import numpy as np
from typing import List, Union


class TEIClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        api_key: str = None,
        client_batch_size: int = 32,
        timeout_seconds: float = 60.0,
    ):
        # Normalize trailing slashes and construct TEI endpoint paths safely.
        self.base_url = base_url.rstrip("/")
        self.embed_endpoint = f"{self.base_url}/embed"
        self.predict_endpoint = f"{self.base_url}/predict"

        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        self.client_batch_size = client_batch_size
        self.timeout_seconds = timeout_seconds

    def encode(self, sentences: Union[str, List[str]]) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]

        all_embeddings = []

        # Process in batches to respect TEI client_batch_size
        for i in range(0, len(sentences), self.client_batch_size):
            batch = sentences[i : i + self.client_batch_size]
            payload = {"inputs": batch, "normalize": True}

            response = requests.post(
                self.embed_endpoint,
                json=payload,
                headers=self.headers,
                timeout=self.timeout_seconds,
            )

            if response.status_code != 200:
                # Fallback to feature extraction route if /embed fails with 404
                if response.status_code == 404:
                    response = requests.post(
                        self.predict_endpoint,
                        json=payload,
                        headers=self.headers,
                        timeout=self.timeout_seconds,
                    )

                if response.status_code != 200:
                    raise RuntimeError(
                        f"TEI Request failed with status {response.status_code}: {response.text}"
                    )

            embeddings = response.json()

            if isinstance(embeddings, dict) and "embeddings" in embeddings:
                all_embeddings.extend(embeddings["embeddings"])
            elif isinstance(embeddings, dict) and "data" in embeddings:
                vectors = [item["embedding"] for item in embeddings["data"]]
                all_embeddings.extend(vectors)
            else:
                all_embeddings.extend(embeddings)

        return np.array(all_embeddings, dtype=float)
