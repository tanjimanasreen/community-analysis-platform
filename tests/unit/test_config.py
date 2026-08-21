import pytest
from pathlib import Path
from src.config.loader import load_config, validate_run_config
from src.tracking.factory import parse_tracking_settings


def test_sample_config_remains_valid():
    """
    Proves that the primary sample configuration remains valid
    as the schema evolves.
    """
    config_path = Path("tests/configs/test_single_month.yml")
    assert config_path.exists(), "Sample configuration file must exist"

    # Should not raise an exception
    config = load_config(str(config_path))
    validate_run_config(config)

    assert config.get("data_type") == "twitter"
    assert config.get("content_type") == "reply"
    assert config.get("lda", {}).get("num_topics") == 15
    assert config.get("theme", {}).get("render_visuals") is False


def test_canonical_theme_provider_fallback_settings_remain_valid():
    config = load_config("tests/configs/test_single_month.yml")
    config["theme_provider"] = {
        "primary": "mock",
        "fallback": True,
        "fallback_chain": ["mock"],
    }

    validate_run_config(config)


def test_obsolete_theme_fallback_is_rejected():
    config = load_config("tests/configs/test_single_month.yml")
    config.setdefault("theme", {})["fallback"] = True

    with pytest.raises(ValueError, match=r"theme\.fallback.*theme_provider\.fallback"):
        validate_run_config(config)


def test_obsolete_theme_fallback_chain_is_rejected():
    config = load_config("tests/configs/test_single_month.yml")
    config.setdefault("theme", {})["fallback_chain"] = ["mock"]

    with pytest.raises(
        ValueError, match=r"theme\.fallback_chain.*theme_provider\.fallback_chain"
    ):
        validate_run_config(config)


def test_analytical_theme_settings_remain_valid():
    config = load_config("tests/configs/test_single_month.yml")
    config["theme"] = {
        "render_visuals": False,
        "similarity_model": "paraphrase-MiniLM-L6-v2",
        "max_workers": 2,
    }

    validate_run_config(config)


def test_tracking_is_disabled_when_sample_config_omits_section():
    config = load_config("tests/configs/test_single_month.yml")
    config.pop("tracking", None)
    validate_run_config(config)
    settings = parse_tracking_settings(config, Path.cwd())
    assert settings.enabled is False
    assert settings.backend is None


def test_invalid_enabled_tracking_config_is_rejected():
    config = load_config("tests/configs/test_single_month.yml")
    config["tracking"] = {
        "enabled": True,
        "backend": "mlflow",
        "experiment_name": "tests",
        "backend_store_path": "../escape.db",
        "artifact_root": ".mlflow/artifacts",
        "nested_stage_runs": True,
        "failure_policy": "warn",
        "log_artifact_references": True,
    }
    with pytest.raises(ValueError, match="escapes the repository root"):
        validate_run_config(config)


def test_similarity_tei_profile_prefers_explicit_profile_environment(monkeypatch):
    from src.config.settings import get_tei_client_settings

    monkeypatch.setenv("TEI_BASE_URL", "http://legacy.test:8080")
    monkeypatch.setenv("TEI_MODEL_ID", "legacy/model")
    monkeypatch.setenv("TEI_SIMILARITY_BASE_URL", "http://similarity.test:9080")
    monkeypatch.setenv(
        "TEI_SIMILARITY_MODEL_ID",
        "sentence-transformers/paraphrase-MiniLM-L6-v2",
    )
    monkeypatch.setenv("TEI_SIMILARITY_REVISION", "pinned-revision")

    settings = get_tei_client_settings()

    assert str(settings.base_url).rstrip("/") == "http://similarity.test:9080"
    assert settings.model_id == "sentence-transformers/paraphrase-MiniLM-L6-v2"
    assert settings.revision == "pinned-revision"


def test_similarity_tei_profile_reads_profile_values_from_dotenv(monkeypatch, tmp_path):
    from src.config.settings import get_tei_client_settings

    for name in (
        "TEI_SIMILARITY_BASE_URL",
        "TEI_SIMILARITY_MODEL_ID",
        "TEI_SIMILARITY_REVISION",
        "TEI_BASE_URL",
        "TEI_MODEL_ID",
        "TEI_REVISION",
    ):
        monkeypatch.delenv(name, raising=False)
    (tmp_path / ".env").write_text(
        "TEI_BASE_URL=http://legacy.test:8080\n"
        "TEI_SIMILARITY_BASE_URL=http://similarity.test:9080\n"
        "TEI_MODEL_ID=legacy/model\n"
        "TEI_SIMILARITY_MODEL_ID=sentence-transformers/paraphrase-MiniLM-L6-v2\n"
        "TEI_REVISION=legacy-revision\n"
        "TEI_SIMILARITY_REVISION=pinned-revision\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = get_tei_client_settings()

    assert str(settings.base_url).rstrip("/") == "http://similarity.test:9080"
    assert settings.model_id == "sentence-transformers/paraphrase-MiniLM-L6-v2"
    assert settings.revision == "pinned-revision"


def test_database_settings_are_loaded_from_graph_db_environment(monkeypatch):
    from src.config.loader import get_database_config

    monkeypatch.setenv("GRAPH_DB_ENGINE", "future-graph")
    monkeypatch.setenv("GRAPH_DB_URI", "bolt://graph.example:9999")
    monkeypatch.setenv("GRAPH_DB_USER", "graph-user")
    monkeypatch.setenv("GRAPH_DB_PASSWORD", "graph-password")

    config = get_database_config({})

    assert config == {
        "engine": "future-graph",
        "uri": "bolt://graph.example:9999",
        "user": "graph-user",
        "password": "graph-password",
    }


def test_database_settings_default_to_memgraph(monkeypatch, tmp_path):
    from src.config.loader import get_database_config

    for name in (
        "GRAPH_DB_ENGINE",
        "GRAPH_DB_URI",
        "GRAPH_DB_USER",
        "GRAPH_DB_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)

    config = get_database_config({})

    assert config["engine"] == "memgraph"
    assert config["uri"] == "bolt://localhost:7687"


def test_database_section_in_run_yaml_is_rejected():
    config = load_config("tests/configs/test_single_month.yml")
    config["database"] = {"engine": "memgraph", "uri": "bolt://ignored:7687"}

    with pytest.raises(
        ValueError, match="Database connection settings are environment-only"
    ):
        validate_run_config(config)


def test_database_section_is_rejected_when_database_config_is_resolved():
    from src.config.loader import get_database_config

    with pytest.raises(
        ValueError, match="Database connection settings are environment-only"
    ):
        get_database_config({"database": {"engine": "memgraph"}})


def test_database_section_in_longitudinal_dataset_is_rejected():
    from src.config.loader import validate_database_config_policy

    config = {
        "longitudinal_datasets": [
            {"month": "march", "database": {"uri": "bolt://ignored:7687"}}
        ]
    }

    with pytest.raises(ValueError, match=r"longitudinal_datasets\[0\]\.database"):
        validate_database_config_policy(config)
