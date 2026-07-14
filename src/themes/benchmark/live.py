from __future__ import annotations

from src.themes.benchmark.contracts import ThemeBenchmarkError


class LiveRequestBudget:
    def __init__(self, *, provider_name: str, max_outbound_requests: int):
        self.provider_name = provider_name
        self.max_outbound_requests = max_outbound_requests
        self.used = 0

    def consume(self) -> None:
        if self.used >= self.max_outbound_requests:
            raise ThemeBenchmarkError(
                f"{self.provider_name} request cap exhausted: "
                f"{self.used}/{self.max_outbound_requests}"
            )
        self.used += 1
