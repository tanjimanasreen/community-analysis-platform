from unittest.mock import MagicMock

import pandas as pd

import src.pipelines.theme_pipeline as theme_pipeline


def test_one_provider_instance_handles_batch(monkeypatch, tmp_path):
    monthly_data = {
        "january": pd.DataFrame({"topic": ["A"]}),
        "february": pd.DataFrame({"topic": ["B"]}),
        "march": pd.DataFrame({"topic": ["C"]}),
    }

    constructed_provider = MagicMock(name="constructed-provider")
    build_provider = MagicMock(return_value=constructed_provider)
    recorded_providers = []

    def fake_process(df, provider):
        recorded_providers.append(provider)
        return df

    monkeypatch.setattr(
        theme_pipeline.factory,
        "build_theme_provider",
        build_provider,
    )
    monkeypatch.setattr(
        theme_pipeline,
        "process_single_file_themes",
        fake_process,
    )
    monkeypatch.setattr(
        theme_pipeline,
        "get_community_transition",
        lambda *_args, **_kwargs: pd.DataFrame(
            {"source": [], "target": [], "score": []}
        ),
    )
    monkeypatch.setattr(
        theme_pipeline,
        "get_path_info",
        lambda *_args, **_kwargs: ([], [], [], []),
    )
    monkeypatch.setattr(
        theme_pipeline,
        "find_all_sankey_paths",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        theme_pipeline,
        "extract_themes",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        theme_pipeline,
        "build_community_path_artifact",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )
    monkeypatch.setattr(
        theme_pipeline,
        "build_membership_mobility_artifact",
        lambda *_args, **_kwargs: pd.DataFrame(),
    )

    theme_pipeline.run_theme_pipeline_from_monthly_data(
        monthly_data_dict=monthly_data,
        year="2023",
        content_type="messages",
        output_dir=str(tmp_path),
        config={"theme_provider": {"primary": "mock"}},
        render_visuals=False,
    )

    build_provider.assert_called_once()
    assert len(recorded_providers) == len(monthly_data)
    assert all(provider is constructed_provider for provider in recorded_providers)
