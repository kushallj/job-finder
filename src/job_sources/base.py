"""The one interface every job source implements, plus a composable adapter.

Composition over inheritance: a source is data (name, tier, an `enabled` check, a fetch
coroutine), not a class hierarchy. Wrapping an existing client takes a few lines in
`sources.py`, and tests can build fake sources the same way.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from src.job_sources.models import JobRecord, SearchQuery, Tier

RawFetch = Callable[[SearchQuery], Awaitable[list[Mapping[str, Any]]]]


@runtime_checkable
class JobSource(Protocol):
    name: str
    tier: Tier

    @property
    def enabled(self) -> bool: ...

    async def fetch(self, query: SearchQuery) -> list[JobRecord]: ...


def _always() -> bool:
    return True


@dataclass(frozen=True, slots=True)
class CallableSource:
    """Adapts any `async (query) -> list[dict]` into a `JobSource`.

    `fetch_raw` returns provider dicts (normalized or legacy); they're mapped to
    `JobRecord` here so no source has to know the canonical type.
    """

    name: str
    tier: Tier
    fetch_raw: RawFetch
    is_enabled: Callable[[], bool] = _always
    description: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.is_enabled())

    async def fetch(self, query: SearchQuery) -> list[JobRecord]:
        rows = await self.fetch_raw(query)
        records = (JobRecord.from_dict(row, self.name) for row in rows or [])
        return [r for r in records if r is not None]
