import pytest

from src.themes.benchmark.contracts import ThemeBenchmarkError, ThemeBenchmarkRequest
from src.providers.mock import BenchmarkMockProvider
from src.providers.routing import RoutingBenchmarkProvider

class FailingMockProvider(BenchmarkMockProvider):
    def __init__(self, error_message="Simulated rate limit"):
        self.error_message = error_message
        super().__init__()
        
    def generate(self, request):
        raise ThemeBenchmarkError(self.error_message)


def test_routing_provider_success():
    mock1 = BenchmarkMockProvider()
    routing = RoutingBenchmarkProvider([mock1])
    
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
    result = routing.generate(req)
    assert result["themes"] == [{"name": "Benchmark General Theme", "keywords": ["apple", "banana"]}]


def test_routing_provider_fallback():
    failing = FailingMockProvider()
    success = BenchmarkMockProvider()
    
    routing = RoutingBenchmarkProvider([failing, success])
    
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
    
    # We add a fake benchmark metadata so the fallback metadata is captured
    orig_generate = success.generate
    def patched_generate(request):
        res = orig_generate(request)
        res["_benchmark_metadata"] = {}
        return res
        
    success.generate = patched_generate
    
    result = routing.generate(req)
    assert result["themes"] == [{"name": "Benchmark General Theme", "keywords": ["apple", "banana"]}]
    
    fallback_attempts = result["_benchmark_metadata"]["fallback_attempts"]
    assert len(fallback_attempts) == 1
    assert fallback_attempts[0]["provider_id"] == failing.metadata.provider_id
    assert "Simulated rate limit" in fallback_attempts[0]["error"]


def test_routing_provider_exhausted():
    failing1 = FailingMockProvider("Error 1")
    failing2 = FailingMockProvider("Error 2")
    
    routing = RoutingBenchmarkProvider([failing1, failing2])
    
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
    
    with pytest.raises(ThemeBenchmarkError, match="exhausted all fallbacks"):
        routing.generate(req)
