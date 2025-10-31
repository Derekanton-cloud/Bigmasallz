"""Live statistics service for reporting agent performance."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from app.models.stats import LiveStats


@dataclass
class _InternalStats:
    generated_rows: int = 0
    total_schema_tokens: int = 0
    total_data_tokens: int = 0
    tasks_running: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_update_ns: int = time.time_ns()


class StatsService:
    """Keep light-weight counters updated across async workers."""

    def __init__(self) -> None:
        self._stats = _InternalStats()
        self._lock = asyncio.Lock()

    def _now_ns(self) -> int:
        return time.time_ns()

    async def track_task_created(self) -> None:
        async with self._lock:
            # No-op for now but keeps pattern symmetrical
            self._stats.last_update_ns = self._now_ns()

    async def track_task_running(self) -> None:
        async with self._lock:
            self._stats.tasks_running += 1
            self._stats.last_update_ns = self._now_ns()

    async def track_task_completed(self) -> None:
        async with self._lock:
            if self._stats.tasks_running > 0:
                self._stats.tasks_running -= 1
            self._stats.tasks_completed += 1
            self._stats.last_update_ns = self._now_ns()

    async def track_task_failed(self) -> None:
        async with self._lock:
            if self._stats.tasks_running > 0:
                self._stats.tasks_running -= 1
            self._stats.tasks_failed += 1
            self._stats.last_update_ns = self._now_ns()

    async def track_rows_generated(self, rows: int) -> None:
        async with self._lock:
            self._stats.generated_rows += rows
            self._stats.last_update_ns = self._now_ns()

    async def track_schema_tokens(self, tokens: int) -> None:
        async with self._lock:
            self._stats.total_schema_tokens += tokens
            self._stats.last_update_ns = self._now_ns()

    async def track_data_tokens(self, tokens: int) -> None:
        async with self._lock:
            self._stats.total_data_tokens += tokens
            self._stats.last_update_ns = self._now_ns()

    async def snapshot(self) -> LiveStats:
        async with self._lock:
            elapsed_seconds = (self._now_ns() - self._stats.last_update_ns) / 1e9
            avg_rows = 0.0
            if elapsed_seconds > 0:
                avg_rows = self._stats.generated_rows / max(elapsed_seconds, 1.0)
            return LiveStats(
                generated_rows=self._stats.generated_rows,
                avg_rows_per_sec=avg_rows,
                active_tasks=self._stats.tasks_running,
                tokens_spent_schema=self._stats.total_schema_tokens,
                tokens_spent_data=self._stats.total_data_tokens,
            )


stats_service = StatsService()
