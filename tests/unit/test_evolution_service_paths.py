from __future__ import annotations

import json

import pandas as pd

from src.api.services.evolution_service import EvolutionService


class FakeReader:
    def __init__(self, frames: dict[str, pd.DataFrame], config: dict):
        self.frames = frames
        self.config = config

    def get_record(self, run_id: str, artifact_key: str):
        assert run_id == "run-1"
        if artifact_key not in self.frames:
            from src.api.errors import ArtifactNotFoundError

            raise ArtifactNotFoundError(run_id, artifact_key)
        return artifact_key

    def read_parquet_record(self, run_id: str, record):
        assert run_id == "run-1"
        return self.frames[record].copy()

    @staticmethod
    def page(frame: pd.DataFrame, *, limit: int, offset: int):
        page = frame.iloc[offset : offset + limit]
        return page.to_dict(orient="records"), len(frame)

    def read_safe_config(self, run_id: str):
        assert run_id == "run-1"
        return self.config


def _reader() -> FakeReader:
    path_rows = [
        {
            "path_id": "path-a",
            "display_order": 1,
            "step_index": 0,
            "month": "01",
            "community_key": "1",
            "community_id": "1",
            "member_count": 3,
            "members": json.dumps(["u1", "u2", "u3"]),
            "previous_month": None,
            "previous_community_key": None,
            "previous_community_id": None,
            "jaccard_from_previous": None,
            "retained_count": None,
            "absolute_theme": "Politics",
            "weighted_theme": "Politics",
            "general_theme": "Politics",
        },
        {
            "path_id": "path-a",
            "display_order": 1,
            "step_index": 1,
            "month": "02",
            "community_key": "2",
            "community_id": "2",
            "member_count": 3,
            "members": json.dumps(["u1", "u2", "u4"]),
            "previous_month": "01",
            "previous_community_key": "1",
            "previous_community_id": "1",
            "jaccard_from_previous": 0.5,
            "retained_count": 2,
            "absolute_theme": "Policy",
            "weighted_theme": "Policy",
            "general_theme": "Policy",
        },
    ]
    mobility_rows = [
        {
            "path_id": "path-a",
            "display_order": 1,
            "step_index": 0,
            "month": "01",
            "community_key": "1",
            "community_id": "1",
            "member_count": 3,
            "size_delta": None,
            "existing_count": 3,
            "new_count": 0,
            "lost_count": 0,
            "reappearing_count": 0,
            "members": json.dumps(["u1", "u2", "u3"]),
            "existing_members": json.dumps(["u1", "u2", "u3"]),
            "new_members": "[]",
            "lost_members": "[]",
            "reappearing_members": "[]",
        },
        {
            "path_id": "path-a",
            "display_order": 1,
            "step_index": 1,
            "month": "02",
            "community_key": "2",
            "community_id": "2",
            "member_count": 3,
            "size_delta": 0,
            "existing_count": 2,
            "new_count": 1,
            "lost_count": 1,
            "reappearing_count": 1,
            "members": json.dumps(["u1", "u2", "u4"]),
            "existing_members": json.dumps(["u1", "u2"]),
            "new_members": json.dumps(["u4"]),
            "lost_members": json.dumps(["u3"]),
            "reappearing_members": json.dumps(["u4"]),
        },
    ]
    similarity_rows = [
        {
            "path_id": "path-a",
            "display_order": 1,
            "theme_type": "general",
            "left_step_index": 0,
            "right_step_index": 0,
            "left_month": "01",
            "right_month": "01",
            "left_community_key": "1",
            "right_community_key": "1",
            "left_theme": "Politics",
            "right_theme": "Politics",
            "cosine_similarity": 1.0,
            "embedding_provider": "tei",
            "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
            "embedding_model_revision": "pinned-revision",
        },
        {
            "path_id": "path-a",
            "display_order": 1,
            "theme_type": "general",
            "left_step_index": 0,
            "right_step_index": 1,
            "left_month": "01",
            "right_month": "02",
            "left_community_key": "1",
            "right_community_key": "2",
            "left_theme": "Politics",
            "right_theme": "Policy",
            "cosine_similarity": 0.72,
            "embedding_provider": "tei",
            "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
            "embedding_model_revision": "pinned-revision",
        },
        {
            "path_id": "path-a",
            "display_order": 1,
            "theme_type": "general",
            "left_step_index": 1,
            "right_step_index": 1,
            "left_month": "02",
            "right_month": "02",
            "left_community_key": "2",
            "right_community_key": "2",
            "left_theme": "Policy",
            "right_theme": "Policy",
            "cosine_similarity": 1.0,
            "embedding_provider": "tei",
            "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
            "embedding_model_revision": "pinned-revision",
        },
    ]
    return FakeReader(
        {
            "community_paths": pd.DataFrame(path_rows),
            "community_path_membership": pd.DataFrame(mobility_rows),
            "community_path_theme_similarity": pd.DataFrame(similarity_rows),
        },
        {
            "content_type": "reply",
            "theme": {
                "transition_threshold": 0.5,
                "reply_transition_threshold": 0.0,
                "similarity_provider": "tei",
                "similarity_model": "paraphrase-MiniLM-L6-v2",
                "similarity_model_revision": "pinned-revision",
            },
        },
    )


def test_path_read_models_are_artifact_only_and_preserve_reply_threshold():
    service = EvolutionService(_reader())

    paths = service.paths("run-1")
    assert paths["total"] == 1
    assert paths["paths"][0]["path_id"] == "path-a"
    assert paths["paths"][0]["average_jaccard"] == 0.5
    assert paths["methodology"]["transition_threshold"] == 0.0

    mobility = service.path_membership("run-1", "path-a")
    assert mobility["records"][1]["reappearing_count"] == 1

    similarity = service.path_theme_similarity("run-1", "path-a", theme_type="general")
    assert similarity["matrix"] == [[1.0, 0.72], [0.72, 1.0]]
    assert (
        similarity["embedding_model"] == "sentence-transformers/paraphrase-MiniLM-L6-v2"
    )
    assert similarity["embedding_model_revision"] == "pinned-revision"
