"""MCP tool that uses ChromaDB to deduplicate generated rows."""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from app.repositories.vector_store import get_vector_store


class DeduplicationTool:
    """Identify and register duplicate dataset rows."""

    def __init__(self) -> None:
        self._vector_store = get_vector_store()

    async def filter_new_rows(self, rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = list(rows)
        if not rows:
            return rows
        serialized = [self._serialize(row) for row in rows]
        duplicates = await self._vector_store.find_duplicates(serialized)
        duplicate_set = set(duplicates)
        filtered = [row for row, raw in zip(rows, serialized) if raw not in duplicate_set]
        await self._vector_store.upsert_rows([raw for raw in serialized if raw not in duplicate_set])
        return filtered

    @staticmethod
    def _serialize(row: Dict[str, Any]) -> str:
        return json.dumps(row, sort_keys=True)
