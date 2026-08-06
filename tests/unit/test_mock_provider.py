from __future__ import annotations

import socket

import pytest

from src.providers.mock import BenchmarkMockProvider, MockProvider
from src.themes.benchmark.contracts import ThemeBenchmarkRequest


def _request() -> ThemeBenchmarkRequest:
    return ThemeBenchmarkRequest(
        example_id="offline-mock",
        keyword_mode="general",
        keywords=["apple", "orange"],
        keyword_text="apple, orange",
        system_prompt="Group the supplied keywords into themes.",
        user_prompt="Keywords: apple, orange",
        prompt_hash="prompt-hash",
        input_hash="input-hash",
    )


@pytest.mark.parametrize(
    "provider",
    [
        MockProvider({"Fruit Theme": ["apple", "orange"]}),
        BenchmarkMockProvider(),
    ],
)
def test_mock_providers_never_require_network_for_token_metadata(
    monkeypatch: pytest.MonkeyPatch,
    provider: MockProvider | BenchmarkMockProvider,
) -> None:
    def fail_connect(*args, **kwargs):
        raise AssertionError("offline mock provider attempted network access")

    monkeypatch.setattr(socket.socket, "connect", fail_connect)

    result = provider.generate(_request())
    usage = result["_benchmark_metadata"]["usage"]

    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
    assert usage["total_tokens"] == (
        usage["prompt_tokens"] + usage["completion_tokens"]
    )
