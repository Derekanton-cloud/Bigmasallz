"""Hybrid numeric generator to reduce LLM token expenditure."""
from __future__ import annotations

import random
from typing import Dict, List

from app.models.schema import ColumnSpec


class HybridNumericGenerator:
    """Generate deterministic numeric values for relevant columns."""

    def __init__(self, seed: int = 42) -> None:
        self._seed = seed

    def should_handle(self, column: ColumnSpec) -> bool:
        data_type = column.data_type.lower()
        return any(keyword in data_type for keyword in ("int", "float", "numeric", "decimal"))

    def generate_column(self, column: ColumnSpec, row_count: int, offset: int = 0) -> List[float]:
        rng = random.Random(self._seed + offset)
        values: List[float] = []
        data_type = column.data_type.lower()
        for idx in range(row_count):
            base = rng.uniform(0, 1)
            if "int" in data_type:
                values.append(int(base * 1000 + idx))
            elif "decimal" in data_type or "float" in data_type:
                values.append(round((base * 100) + idx * 0.1, 4))
            else:
                values.append(round(base * 100, 4))
        return values

    def generate_chunk(
        self,
        columns: List[ColumnSpec],
        row_count: int,
        offset: int = 0,
    ) -> Dict[str, List[float]]:
        generated: Dict[str, List[float]] = {}
        for column in columns:
            if self.should_handle(column):
                generated[column.name] = self.generate_column(column, row_count, offset)
        return generated
