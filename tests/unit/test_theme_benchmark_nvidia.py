import pytest
import os
from src.themes.benchmark.contracts import ThemeBenchmarkError, ThemeBenchmarkRequest
from src.providers.nvidia import NvidiaBenchmarkProvider


def test_nvidia_provider_init_requires_allow_live():
    with pytest.raises(ThemeBenchmarkError, match="requires --allow-live"):
        NvidiaBenchmarkProvider(model_id="test", allow_live=False)


def test_nvidia_provider_init_requires_api_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    from src.config.settings import ProviderSettings

    isolated_settings = ProviderSettings(_env_file=None, nvidia_api_key=None)
    monkeypatch.setattr(
        "src.providers.nvidia.get_provider_settings", lambda: isolated_settings
    )
    with pytest.raises(ThemeBenchmarkError, match="NVIDIA_API_KEY must be set"):
        NvidiaBenchmarkProvider(model_id="test", allow_live=True)


class MockChoice:
    def __init__(self, content):
        self.message = type("Message", (), {"content": content})
        self.finish_reason = "stop"


class MockCompletion:
    def __init__(self, content):
        self.choices = [MockChoice(content)]
        self.usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        self.id = "test_id"
        self.model = "test_model"
        self.created = 12345
        self.object = "chat.completion"
        self.system_fingerprint = "test_fp"


class MockCompletionsAPI:
    def __init__(self, response_content):
        self.response_content = response_content

    def create(self, **kwargs):
        if "error" in self.response_content:
            raise Exception(self.response_content)
        return MockCompletion(self.response_content)


class MockChat:
    def __init__(self, response_content):
        self.completions = MockCompletionsAPI(response_content)


class MockClient:
    def __init__(self, response_content):
        self.chat = MockChat(response_content)


def test_nvidia_provider_generate_success():
    client = MockClient(
        '{"themes": [{"name": "test_theme", "keyword_indices": [0, 1]}]}'
    )
    provider = NvidiaBenchmarkProvider(
        model_id="meta/llama3-70b-instruct",
        allow_live=True,
        client=client,
        api_key="mock",
    )
    req = ThemeBenchmarkRequest(
        example_id="1",
        keyword_mode="general",
        keywords=["apple", "banana"],
        keyword_text="apple banana",
        system_prompt="sys",
        user_prompt="user",
        prompt_hash="123",
        input_hash="456",
    )
    result = provider.generate(req)
    assert result["themes"] == [{"name": "test_theme", "keywords": ["apple", "banana"]}]
    assert result["_benchmark_metadata"]["parsed_successfully"] is True


def test_nvidia_provider_generate_retry_failure():
    client = MockClient("rate limit exceeded error")
    provider = NvidiaBenchmarkProvider(
        model_id="meta/llama3-70b-instruct",
        allow_live=True,
        client=client,
        api_key="mock",
        max_retries=1,
        sleep_fn=lambda x: None,
    )
    req = ThemeBenchmarkRequest(
        example_id="1",
        keyword_mode="general",
        keywords=["apple", "banana"],
        keyword_text="apple banana",
        system_prompt="sys",
        user_prompt="user",
        prompt_hash="123",
        input_hash="456",
    )
    with pytest.raises(ThemeBenchmarkError, match="rate_limit"):
        provider.generate(req)
