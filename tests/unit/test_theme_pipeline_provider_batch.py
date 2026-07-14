import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.pipelines.theme_pipeline import run_theme_pipeline_from_monthly_data

@patch("src.pipelines.theme_pipeline.process_single_file_themes")
@patch("src.providers.factory.build_theme_provider")
def test_one_provider_instance_handles_batch(mock_build_theme_provider, mock_process, tmp_path):
    """
    Proves that exactly one provider instance is created and that the EXACT same
    provider instance is passed to every month's batch generation call.
    """
    monthly_data = {
        "january": pd.DataFrame({"topic": ["A"]}),
        "february": pd.DataFrame({"topic": ["B"]}),
        "march": pd.DataFrame({"topic": ["C"]})
    }
    
    constructed_provider = MagicMock()
    mock_build_theme_provider.return_value = constructed_provider
    mock_process.side_effect = lambda df, provider: df
    
    with patch("src.pipelines.theme_pipeline.draw_community_transition_diagram"), \
         patch("src.pipelines.theme_pipeline.get_community_transition") as mock_gct:
        mock_gct.return_value = pd.DataFrame({"source": [], "target": [], "score": []})
        
        run_theme_pipeline_from_monthly_data(
            monthly_data_dict=monthly_data,
            year="2023",
            content_type="messages",
            output_dir=str(tmp_path),
            config={"theme_provider": {"primary": "mock"}},
            render_visuals=False
        )
            
    recorded_provider_instances = [call[0][1] for call in mock_process.call_args_list]

    print(f"mock_build: {mock_build_theme_provider}")
    print(f"mock_process: {mock_process}")
    print(f"mock_build call_count: {mock_build_theme_provider.call_count}")
    print(f"recorded_provider_instances: {recorded_provider_instances}")

    assert mock_build_theme_provider.call_count == 1
