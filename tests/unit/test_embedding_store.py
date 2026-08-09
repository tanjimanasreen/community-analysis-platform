from __future__ import annotations

import numpy as np
import pytest

from src.themes.embedding_store import (
    EMBEDDING_COLUMNS,
    EmbeddingContract,
    RecordingEmbeddingModel,
    embedding_key,
)


class FakeProvider:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.closed = False

    def encode(self, sentences):
        texts = [str(value) for value in sentences]
        self.calls.append(texts)
        return np.asarray(
            [[float(len(text)), float(index), 1.0] for index, text in enumerate(texts)],
            dtype=np.float32,
        )

    def close(self) -> None:
        self.closed = True


def _contract(*, revision: str = "abc123") -> EmbeddingContract:
    return EmbeddingContract(
        profile="theme_clustering",
        provider="tei",
        model_id="sentence-transformers/example",
        model_revision=revision,
        normalized=False,
        dimensions=3,
    )


def test_recording_embedder_deduplicates_inference_but_preserves_observation_density():
    provider = FakeProvider()
    recorder = RecordingEmbeddingModel(provider, _contract())

    matrix = recorder.encode(["Theme A", "Theme B", "Theme A"])

    assert provider.calls == [["Theme A", "Theme B"]]
    assert matrix.shape == (3, 3)
    assert matrix.dtype == np.float32
    assert np.array_equal(matrix[0], matrix[2])
    assert recorder.record_count == 2

    # Already-recorded texts do not trigger another provider request.
    again = recorder.encode(["Theme B", "Theme A"])
    assert provider.calls == [["Theme A", "Theme B"]]
    assert np.array_equal(again[0], matrix[1])


def test_embedding_key_is_content_and_model_revision_addressed():
    first = embedding_key("US Immigration Policy", _contract(revision="rev-a"))
    same = embedding_key("US Immigration Policy", _contract(revision="rev-a"))
    changed_revision = embedding_key(
        "US Immigration Policy", _contract(revision="rev-b")
    )
    changed_text = embedding_key("us immigration policy", _contract(revision="rev-a"))

    assert first == same
    assert first != changed_revision
    assert first != changed_text


def test_embedding_contract_requires_pinned_revision_and_dimensions():
    with pytest.raises(ValueError, match="model_revision"):
        _contract(revision="")
    with pytest.raises(ValueError, match="dimensions"):
        EmbeddingContract(
            profile="theme_clustering",
            provider="tei",
            model_id="model",
            model_revision="revision",
            normalized=False,
            dimensions=0,
        )


def test_recording_embedder_rejects_unexpected_dimension():
    provider = FakeProvider()
    recorder = RecordingEmbeddingModel(
        provider,
        EmbeddingContract(
            profile="theme_clustering",
            provider="tei",
            model_id="model",
            model_revision="revision",
            normalized=False,
            dimensions=384,
        ),
    )

    with pytest.raises(RuntimeError, match="expected 384"):
        recorder.encode(["Theme A"])


def test_embedding_parquet_uses_fixed_size_float32_vectors(tmp_path):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    del pa

    provider = FakeProvider()
    recorder = RecordingEmbeddingModel(provider, _contract())
    recorder.encode(["Theme B", "Theme A", "Theme B"])
    path = recorder.write_parquet(tmp_path / "embeddings.parquet")

    table = pq.read_table(path)
    assert table.column_names == EMBEDDING_COLUMNS
    assert table.num_rows == 2
    assert (
        str(table.schema.field("embedding").type)
        == "fixed_size_list<element: float>[3]"
    )
    assert table.column("dtype").to_pylist() == ["float32", "float32"]
    assert table.column("model_revision").to_pylist() == ["abc123", "abc123"]


def test_empty_embedding_artifact_is_still_schema_valid(tmp_path):
    pq = pytest.importorskip("pyarrow.parquet")

    recorder = RecordingEmbeddingModel(FakeProvider(), _contract())
    path = recorder.write_parquet(tmp_path / "empty.parquet")

    table = pq.read_table(path)
    assert table.column_names == EMBEDDING_COLUMNS
    assert table.num_rows == 0
