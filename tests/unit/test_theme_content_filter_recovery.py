from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.providers.base import ProviderSafetyError, build_theme_request
from src.reporting.output_contract import (
    THEME_GENERATION_PROVENANCE_COLUMNS as CONTRACT_PROVENANCE_COLUMNS,
    get_required_columns_by_artifact,
)
from src.themes.benchmark.contracts import (
    OUTPUT_SCHEMA_VERSION,
    THEME_OUTPUT_JSON_SCHEMA,
    THEME_PROMPT_CONTRACT_VERSION,
    ThemeBenchmarkError,
    build_theme_output_json_schema,
    normalize_indexed_theme_payload,
)
from src.themes.benchmark.dataset import (
    RAW_SYSTEM_TEMPLATE,
    RAW_USER_TEMPLATE,
    build_requests,
)
from src.themes.theme_generation import (
    THEME_GENERATION_PROVENANCE_COLUMNS,
    build_theme_generation_coverage,
    generate_llm_themes,
)
from src.themes.theme_similarity import calculate_sentence_similarity_with_missing

FAILED_PAYLOAD = [
    "status",
    "twitter",
    "relations",
    "commission",
    "des",
    "avec",
    "willy",
    "fog",
    "pedo",
    "dossier",
    "cowboys",
    "hard",
    "bachand",
    "cocks",
    "monsieur",
    "zoophiliac",
    "zoophiliac_pedo",
    "sissy",
    "legal",
    "mating",
    "bbc",
    "ram",
    "boner",
    "dogs",
    "girl",
    "breeding",
]
FAILED_HASH = "5d11a25c48676b2b85f31a50403ac3c47a25f794eecb9c8fb44a252e4b1d8ee4"
RETWEET_BOUNDARY_PAYLOAD = [
    "muslimban",
    "trump",
    "maga",
    "europe",
    "nobannowall",
    "migrants_europe",
    "maga_vets",
    "infowars_drudgereport",
    "foxnews_breitbart",
    "ban",
    "executive_order",
    "muslim",
]
RETWEET_BOUNDARY_HASH = (
    "cb0db3cac2295a5ebc60af239977dcc9bdab3bdb054f3eee6fda917aaf750917"
)


def test_v2_wire_contract_reconstructs_exact_keyword_evidence():
    parsed = {
        "themes": [
            {
                "name": "Faithful category-level label",
                "keyword_indices": [3, 1, 3],
            }
        ]
    }
    result = normalize_indexed_theme_payload(
        parsed, ["first", "second", "third", "fourth"]
    )

    assert result == [
        {
            "name": "Faithful category-level label",
            "keywords": ["fourth", "second"],
        }
    ]
    item_properties = THEME_OUTPUT_JSON_SCHEMA["properties"]["themes"]["items"][
        "properties"
    ]
    assert "keyword_indices" in item_properties
    assert "keywords" not in item_properties
    assert item_properties["keyword_indices"]["minItems"] == 1
    assert "maximum" not in item_properties["keyword_indices"]["items"]
    assert THEME_PROMPT_CONTRACT_VERSION == "v3"
    assert OUTPUT_SCHEMA_VERSION == 2


@pytest.mark.parametrize("bad_index", [-1, 4, "1", 1.5, True])
def test_v2_wire_contract_rejects_invalid_indices(bad_index):
    with pytest.raises(ThemeBenchmarkError, match="schema_invalid"):
        normalize_indexed_theme_payload(
            {"themes": [{"name": "Theme", "keyword_indices": [bad_index]}]},
            ["a", "b", "c", "d"],
        )


def test_v2_wire_contract_rejects_empty_supporting_indices():
    with pytest.raises(ThemeBenchmarkError, match="non-empty"):
        normalize_indexed_theme_payload(
            {"themes": [{"name": "Theme", "keyword_indices": []}]},
            ["a", "b"],
        )


@pytest.mark.parametrize(
    ("keyword_count", "expected_maximum"),
    [(1, 0), (5, 4), (12, 11), (26, 25)],
)
def test_request_local_schema_bounds_indices_to_exact_keyword_count(
    keyword_count, expected_maximum
):
    schema = build_theme_output_json_schema(keyword_count)
    index_items = schema["properties"]["themes"]["items"]["properties"][
        "keyword_indices"
    ]["items"]

    assert index_items == {
        "type": "integer",
        "minimum": 0,
        "maximum": expected_maximum,
    }
    canonical_items = THEME_OUTPUT_JSON_SCHEMA["properties"]["themes"]["items"][
        "properties"
    ]["keyword_indices"]["items"]
    assert "maximum" not in canonical_items


def test_request_local_schema_rejects_empty_keyword_payload():
    with pytest.raises(ThemeBenchmarkError, match="at least one input keyword"):
        build_theme_output_json_schema(0)


def test_retweet_quote_boundary_payload_keeps_hash_and_explicit_zero_based_ids():
    request = build_theme_request(RETWEET_BOUNDARY_PAYLOAD)

    assert request.input_hash == RETWEET_BOUNDARY_HASH
    assert request.prompt_contract_version == "v3"
    assert '[0] "muslimban"' in request.user_prompt
    assert '[11] "muslim"' in request.user_prompt
    assert "[12]" not in request.user_prompt
    assert '"maximum": 11' in request.system_prompt


def test_benchmark_request_uses_same_explicit_ids_and_bounds():
    example = {
        "example_id": "twitter_retweet_quote_2017_01_row0071",
        "general_keyword_text": ", ".join(RETWEET_BOUNDARY_PAYLOAD),
        "general_keywords": RETWEET_BOUNDARY_PAYLOAD,
        "absolute_keyword_text": ", ".join(RETWEET_BOUNDARY_PAYLOAD),
        "absolute_keywords": RETWEET_BOUNDARY_PAYLOAD,
        "weighted_keyword_text": "trump, maga",
        "weighted_keywords": ["trump", "maga"],
        "input_hash": "fixture-input-hash",
    }

    requests = build_requests([example])
    general = next(request for request in requests if request.keyword_mode == "general")
    weighted = next(
        request for request in requests if request.keyword_mode == "weighted"
    )

    assert '[0] "muslimban"' in general.user_prompt
    assert '[11] "muslim"' in general.user_prompt
    assert '"maximum": 11' in general.system_prompt
    assert '"maximum": 1' in weighted.system_prompt
    assert general.prompt_contract_version == "v3"


def test_twelve_keyword_boundary_accepts_11_and_rejects_12():
    valid = normalize_indexed_theme_payload(
        {"themes": [{"name": "Policy", "keyword_indices": [11]}]},
        RETWEET_BOUNDARY_PAYLOAD,
    )
    assert valid[0]["keywords"] == ["muslim"]

    with pytest.raises(ThemeBenchmarkError, match="keyword index 12 is out of range"):
        normalize_indexed_theme_payload(
            {"themes": [{"name": "Policy", "keyword_indices": [12]}]},
            RETWEET_BOUNDARY_PAYLOAD,
        )


def test_prompt_v3_preserves_severity_and_uses_explicit_zero_based_ids():
    system = RAW_SYSTEM_TEMPLATE.lower()
    user = RAW_USER_TEMPLATE.lower()

    assert "faithful" in system
    assert "descriptive" in system
    assert "non-endorsing" in system
    assert "severity" in system
    assert "do not euphemize" in system
    assert "do not infer or introduce claims that are stronger" in system
    assert "zero-based keyword ids" in user
    assert "bracketed ids" in user
    assert "one-based" in user
    assert "reproduce" in system
    assert "do not reproduce" in user


def test_confirmed_sensitive_payload_hash_is_unchanged():
    request = build_theme_request(FAILED_PAYLOAD)

    assert request.input_hash == FAILED_HASH
    assert request.prompt_contract_version == "v3"
    assert request.output_schema_version == 2
    assert request.keywords == FAILED_PAYLOAD


class _RecoveryProvider:
    metadata = SimpleNamespace(provider_id="openai", model_id="gpt-5-nano")
    run_metrics = {"cache_hits": 0, "outbound_requests": 0}

    def __init__(self):
        self.calls: list[tuple[str, ...]] = []

    def generate_theme(self, keywords: list[str]) -> dict:
        payload = tuple(keywords)
        self.calls.append(payload)
        if "filtered-a" in payload or "filtered-b" in payload:
            request = build_theme_request(keywords)
            raise ProviderSafetyError(
                category="content_filter",
                stage="completion",
                provider_id="openai",
                model_id="gpt-5-nano",
                input_hash=request.input_hash,
                prompt_hash=request.prompt_hash,
                diagnostics={
                    "content_filter_summary": "completion:sexual:high:blocked"
                },
            )
        return {"Generated Theme": list(keywords[:1])}


def _theme_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "absolute_community": [9, 10, 11],
            "weighted_community": [7, 8, 9],
            "absolute_unigram_keywords": [
                ["filtered-a"],
                ["ordinary"],
                ["filtered-b"],
            ],
            "absolute_bigram_keywords": [[], [], []],
            # First row makes absolute == general so one unique request backs
            # two analytical source assignments, matching the forensic case.
            "weighted_unigram_keywords": [[], ["weighted"], []],
            "weighted_bigram_keywords": [[], [], []],
        }
    )


def test_multiple_safety_failures_are_payload_scoped_and_provenance_is_preserved():
    provider = _RecoveryProvider()
    provenance: list[dict] = []

    result = generate_llm_themes(
        provider,
        _theme_frame(),
        max_workers=3,
        provenance_records=provenance,
        year="2019",
        month="02",
    )

    assert result.loc[0, "absolute_theme_names"] is None
    assert result.loc[0, "general_theme_names"] is None
    assert result.loc[1, "absolute_theme_names"] == "Generated Theme"
    assert result.loc[2, "absolute_theme_names"] is None
    assert len(provider.calls) == len(set(provider.calls))

    filtered_a_rows = [
        row for row in provenance if row["provider_keywords"] == ["filtered-a"]
    ]
    assert {row["keyword_kind"] for row in filtered_a_rows} == {"absolute", "general"}
    assert len({row["input_hash"] for row in filtered_a_rows}) == 1
    assert all(row["status"] == "content_filter_unavailable" for row in filtered_a_rows)
    assert all(row["failure_stage"] == "completion" for row in filtered_a_rows)


def test_provenance_schema_is_registered_in_output_contract():
    assert list(THEME_GENERATION_PROVENANCE_COLUMNS) == CONTRACT_PROVENANCE_COLUMNS
    assert (
        get_required_columns_by_artifact()["theme_generation_provenance"]
        == CONTRACT_PROVENANCE_COLUMNS
    )


def test_coverage_is_source_aware_and_unique_hash_aggregation_is_deterministic():
    rows = [
        {"input_hash": "same", "status": "content_filter_unavailable"},
        {"input_hash": "same", "status": "generated"},
        {"input_hash": "other", "status": "policy_refusal_unavailable"},
    ]

    coverage = build_theme_generation_coverage(rows)

    assert coverage == {
        "unique_payloads_requested": 2,
        "unique_payloads_generated": 1,
        "unique_payloads_unavailable": 1,
        "source_assignments_requested": 3,
        "source_assignments_generated": 1,
        "source_assignments_unavailable": 2,
        "content_filter_count": 1,
        "policy_refusal_count": 1,
        "partial": True,
    }


def test_unapproved_typed_safety_category_is_not_silently_recovered():
    class UnknownSafetyProvider(_RecoveryProvider):
        def generate_theme(self, keywords: list[str]) -> dict:
            request = build_theme_request(keywords)
            raise ProviderSafetyError(
                category="unknown_policy_state",
                stage="unknown",
                provider_id="openai",
                model_id="gpt-5-nano",
                input_hash=request.input_hash,
                prompt_hash=request.prompt_hash,
            )

    with pytest.raises(ProviderSafetyError, match="unknown_policy_state"):
        generate_llm_themes(UnknownSafetyProvider(), _theme_frame(), max_workers=2)


def test_unexpected_provider_error_still_aborts_batch():
    class BrokenProvider(_RecoveryProvider):
        def generate_theme(self, keywords: list[str]) -> dict:
            raise RuntimeError("programming/configuration failure")

    with pytest.raises(RuntimeError, match="programming/configuration failure"):
        generate_llm_themes(BrokenProvider(), _theme_frame(), max_workers=2)


def test_missing_theme_is_never_sent_to_embedding_model():
    class RecordingModel:
        def __init__(self):
            self.calls = []

        def encode(self, sentences):
            self.calls.append(list(sentences))
            return np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float)

    model = RecordingModel()
    matrix = calculate_sentence_similarity_with_missing(
        ["Theme A", None, "Theme B", ""], model=model
    )

    assert model.calls == [["Theme A", "Theme B"]]
    assert np.isnan(matrix[0, 1])
    assert np.isnan(matrix[1, 2])
    assert matrix[0, 0] == pytest.approx(1.0)
    assert matrix[2, 2] == pytest.approx(1.0)


def test_theme_stage_cache_uses_runtime_prompt_contract_not_dataset_yaml(tmp_path):
    from src.orchestration.hashing import theme_cache_key_fn
    from src.orchestration.models import (
        ArtifactReference,
        ThemeInputBundle,
        ValidatedRunConfiguration,
    )

    artifact = ArtifactReference(
        path=str(tmp_path / "input.parquet"),
        sha256="a" * 64,
        media_type="application/octet-stream",
    )
    bundle = ThemeInputBundle(monthly_topic_outputs={"02": artifact})

    def key(prompt_version: str):
        config = ValidatedRunConfiguration(
            config_digest="digest",
            output_root=str(tmp_path),
            raw_config={
                "data_type": "telegram",
                "content_type": "forward",
                "year": "2019",
                "prompt_version": prompt_version,
                "theme_provider": {"primary": "openai:gpt-5-nano"},
                "theme": {"render_visuals": False},
            },
        )
        return theme_cache_key_fn(None, {"input_bundle": bundle, "config": config})

    assert key("v1") == key("stale-config-value")
