import pytest
from src.themes.providers.factory import ProviderFactory
from src.themes.providers.mock_provider import MockThemeSettings
from src.config.defaults import DEFAULT_CONFIG

def test_theme_generation_contract_mock_provider():
    # Ensure ProviderFactory returns a valid provider for 'mock'
    provider = ProviderFactory.create("mock")
    assert provider is not None
    
    # Check the generate_themes contract
    keywords = ["apple", "banana", "orange"]
    # Mock provider doesn't actually need the text, but the contract passes it
    themes_result = provider.generate_themes(
        community_id=0,
        keywords=keywords,
        num_themes=3
    )
    
    # Contract: returns dict[str, list[str]]
    assert isinstance(themes_result, dict)
    assert len(themes_result) > 0
    for theme_name, theme_keywords in themes_result.items():
        assert isinstance(theme_name, str)
        assert isinstance(theme_keywords, list)
        for kw in theme_keywords:
            assert isinstance(kw, str)

def test_analytical_order_downstream_of_lda():
    # The provider receives LDA keywords as input, rather than computing them itself.
    provider = ProviderFactory.create("mock")
    test_keywords = ["test1", "test2"]
    themes_result = provider.generate_themes(
        community_id=1,
        keywords=test_keywords,
        num_themes=1
    )
    # Validate the mock provider uses the input keywords in its mock response
    assert any(kw in themes_result for kw in test_keywords) or \
           any(kw in str(themes_result) for kw in test_keywords)
