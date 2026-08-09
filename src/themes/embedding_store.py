from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import numpy as np

EMBEDDING_ARTIFACT_CONTRACT_VERSION = "1.0"
EMBEDDING_PREPROCESSING_VERSION = "exact-text-v1"
EMBEDDING_DTYPE = "float32"
EMBEDDING_COLUMNS = [
    "embedding_key",
    "text",
    "text_sha256",
    "profile",
    "provider",
    "model_id",
    "model_revision",
    "normalized",
    "preprocessing_version",
    "embedding_contract_version",
    "dimensions",
    "dtype",
    "embedding_sha256",
    "embedding",
]


class EmbeddingModel(Protocol):
    def encode(self, sentences: Sequence[str]) -> np.ndarray: ...


@dataclass(frozen=True)
class EmbeddingContract:
    profile: str
    provider: str
    model_id: str
    model_revision: str
    normalized: bool
    dimensions: int
    preprocessing_version: str = EMBEDDING_PREPROCESSING_VERSION
    contract_version: str = EMBEDDING_ARTIFACT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.profile.strip():
            raise ValueError("embedding profile must be non-empty")
        if not self.provider.strip():
            raise ValueError("embedding provider must be non-empty")
        if not self.model_id.strip():
            raise ValueError("embedding model_id must be non-empty")
        if not self.model_revision.strip():
            raise ValueError("embedding model_revision must be pinned and non-empty")
        if int(self.dimensions) <= 0:
            raise ValueError("embedding dimensions must be positive")


class RecordingEmbeddingModel:
    """Deduplicate inference by exact text while preserving caller row density.

    The caller receives one vector per requested sentence in the original order.
    Internally, each unique content-addressed embedding is computed once and can
    be persisted as an immutable run artifact.
    """

    def __init__(self, provider: EmbeddingModel, contract: EmbeddingContract):
        self.provider = provider
        self.contract = contract
        self._vectors: dict[str, np.ndarray] = {}
        self._texts: dict[str, str] = {}

    def encode(self, sentences: Sequence[str]) -> np.ndarray:
        texts = [str(value) for value in sentences]
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        keys = [embedding_key(text, self.contract) for text in texts]
        missing_keys: list[str] = []
        missing_texts: list[str] = []
        seen_missing: set[str] = set()
        for key, text in zip(keys, texts):
            if key in self._vectors or key in seen_missing:
                continue
            seen_missing.add(key)
            missing_keys.append(key)
            missing_texts.append(text)

        if missing_texts:
            values = np.asarray(self.provider.encode(missing_texts), dtype=np.float32)
            _validate_matrix(values, expected_rows=len(missing_texts))
            if values.shape[1] != self.contract.dimensions:
                raise RuntimeError(
                    "embedding provider returned "
                    f"{values.shape[1]} dimensions; expected {self.contract.dimensions}"
                )
            for key, text, vector in zip(missing_keys, missing_texts, values):
                self._vectors[key] = np.asarray(vector, dtype=np.float32).copy()
                self._texts[key] = text

        matrix = np.vstack([self._vectors[key] for key in keys]).astype(
            np.float32, copy=False
        )
        _validate_matrix(matrix, expected_rows=len(texts))
        return matrix

    @property
    def record_count(self) -> int:
        return len(self._vectors)

    def close(self) -> None:
        close = getattr(self.provider, "close", None)
        if callable(close):
            close()

    def write_parquet(self, path: str | Path) -> Path:
        """Write deterministic fixed-size float32 vectors using PyArrow.

        An empty but schema-valid artifact is written when no embeddings were
        requested. Timestamps are omitted deliberately so identical inputs and
        model contracts produce identical rows.
        """
        import pyarrow as pa
        import pyarrow.parquet as pq

        ordered_keys = sorted(self._vectors)
        dimensions = {int(self._vectors[key].shape[0]) for key in ordered_keys}
        if dimensions and dimensions != {self.contract.dimensions}:
            raise RuntimeError(
                f"embedding dimensions changed within one profile: {sorted(dimensions)}"
            )
        dimension = self.contract.dimensions
        vector_type = pa.list_(pa.float32(), list_size=dimension)

        rows = []
        for key in ordered_keys:
            text = self._texts[key]
            vector = np.asarray(self._vectors[key], dtype=np.float32)
            rows.append(
                {
                    "embedding_key": key,
                    "text": text,
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "profile": self.contract.profile,
                    "provider": self.contract.provider,
                    "model_id": self.contract.model_id,
                    "model_revision": self.contract.model_revision,
                    "normalized": self.contract.normalized,
                    "preprocessing_version": self.contract.preprocessing_version,
                    "embedding_contract_version": self.contract.contract_version,
                    "dimensions": dimension,
                    "dtype": EMBEDDING_DTYPE,
                    "embedding_sha256": hashlib.sha256(
                        vector.tobytes(order="C")
                    ).hexdigest(),
                    "embedding": vector.tolist(),
                }
            )

        arrays = {
            "embedding_key": pa.array(
                [row["embedding_key"] for row in rows], type=pa.string()
            ),
            "text": pa.array([row["text"] for row in rows], type=pa.string()),
            "text_sha256": pa.array(
                [row["text_sha256"] for row in rows], type=pa.string()
            ),
            "profile": pa.array([row["profile"] for row in rows], type=pa.string()),
            "provider": pa.array([row["provider"] for row in rows], type=pa.string()),
            "model_id": pa.array([row["model_id"] for row in rows], type=pa.string()),
            "model_revision": pa.array(
                [row["model_revision"] for row in rows], type=pa.string()
            ),
            "normalized": pa.array(
                [row["normalized"] for row in rows], type=pa.bool_()
            ),
            "preprocessing_version": pa.array(
                [row["preprocessing_version"] for row in rows], type=pa.string()
            ),
            "embedding_contract_version": pa.array(
                [row["embedding_contract_version"] for row in rows], type=pa.string()
            ),
            "dimensions": pa.array(
                [row["dimensions"] for row in rows], type=pa.int32()
            ),
            "dtype": pa.array([row["dtype"] for row in rows], type=pa.string()),
            "embedding_sha256": pa.array(
                [row["embedding_sha256"] for row in rows], type=pa.string()
            ),
            "embedding": pa.array([row["embedding"] for row in rows], type=vector_type),
        }
        table = pa.Table.from_arrays(
            [arrays[column] for column in EMBEDDING_COLUMNS], names=EMBEDDING_COLUMNS
        )

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            pq.write_table(table, temporary, compression="zstd")
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target


def embedding_key(text: str, contract: EmbeddingContract) -> str:
    payload = {
        "contract_version": contract.contract_version,
        "model_id": contract.model_id,
        "model_revision": contract.model_revision,
        "normalized": contract.normalized,
        "dimensions": contract.dimensions,
        "preprocessing_version": contract.preprocessing_version,
        "profile": contract.profile,
        "provider": contract.provider,
        "text": str(text),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"emb_{hashlib.sha256(encoded).hexdigest()}"


def _validate_matrix(values: np.ndarray, *, expected_rows: int) -> None:
    if values.ndim != 2 or values.shape[0] != expected_rows or values.shape[1] == 0:
        raise RuntimeError(
            "embedding provider returned shape "
            f"{values.shape}; expected ({expected_rows}, dimensions)"
        )
    if not np.isfinite(values).all():
        raise RuntimeError("embedding provider returned non-finite values")
