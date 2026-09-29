from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class CollectionRequest:
    search_id: str
    family: str
    term: str
    location: str
    country: str
    lookback_hours: int
    results_wanted: int
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionResult:
    source: str
    request: CollectionRequest
    jobs: list[dict] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0


class Connector(Protocol):
    source: str

    def collect(self, request: CollectionRequest) -> CollectionResult:
        ...
