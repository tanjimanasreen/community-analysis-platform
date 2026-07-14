import pytest
from pathlib import Path
from src.config.loader import load_config, validate_run_config

def test_sample_config_remains_valid():
    """
    Proves that the primary sample configuration remains valid
    as the schema evolves.
    """
    config_path = Path("configs/sample_twitter_reply.yml")
    assert config_path.exists(), "Sample configuration file must exist"
    
    # Should not raise an exception
    config = load_config(str(config_path))
    validate_run_config(config)
    
    assert config.get("data_type") == "twitter"
    assert config.get("content_type") == "reply"
    assert config.get("lda", {}).get("num_topics") == 15
    assert config.get("theme", {}).get("enable_gpt") is False
