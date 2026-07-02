import pandas as pd

from src.pipelines.theme_pipeline import process_single_file_themes, run_theme_pipeline
from src.themes.llm_provider import CachedProvider, MockProvider


def _matched_row(members):
    return {
        "members": str(members),
        "absolute_community": 0,
        "weighted_community": 0,
        "absolute_unigram_keywords": "['apple']",
        "absolute_bigram_keywords": "['big apple']",
        "weighted_unigram_keywords": "['orange']",
        "weighted_bigram_keywords": "['big orange']",
    }


def test_process_single_file_themes_uses_mock_provider():
    df = pd.DataFrame([_matched_row([1, 2])])
    provider = MockProvider({"Fruit Theme": ["apple", "orange"]})

    themed = process_single_file_themes(df, provider)

    assert themed["general_theme_names"].iloc[0] == "Fruit Theme"
    assert themed["absolute_theme_names"].iloc[0] == "Fruit Theme"
    assert themed["weighted_theme_names"].iloc[0] == "Fruit Theme"


def test_run_theme_pipeline_offline_without_rendering(tmp_path):
    input_dir = tmp_path / "lda"
    output_dir = tmp_path / "theme"
    input_dir.mkdir()
    pd.DataFrame([_matched_row([1, 2, 3])]).to_csv(input_dir / "january_2017.csv", index=False)
    pd.DataFrame([_matched_row([1, 2, 3, 4])]).to_csv(input_dir / "february_2017.csv", index=False)

    transitions = run_theme_pipeline(
        input_dir=str(input_dir),
        year="2017",
        content_type="mixed",
        output_dir=str(output_dir),
        provider=MockProvider({"Fruit Theme": ["apple", "orange"]}),
        render_visuals=False,
    )

    assert len(transitions) == 1
    assert (output_dir / "january_2017_with_themes.csv").exists()
    assert (output_dir / "february_2017_with_themes.csv").exists()
    assert (output_dir / "community_transition.csv").exists()


def test_cached_provider_reuses_keyword_response():
    class CountingProvider:
        def __init__(self):
            self.calls = 0

        def generate_theme(self, text):
            self.calls += 1
            return {"Theme": [text]}

    provider = CountingProvider()
    cached = CachedProvider(provider)

    assert cached.generate_theme("apple") == {"Theme": ["apple"]}
    assert cached.generate_theme("apple") == {"Theme": ["apple"]}
    assert provider.calls == 1
