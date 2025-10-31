"""Models for exposing live agent statistics."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LiveStats(BaseModel):
    """Real-time metrics about dataset generation performance."""

    generated_rows: int = Field(0, description="Total number of rows generated")
    avg_rows_per_sec: float = Field(0.0, description="Rolling average throughput")
    active_tasks: int = Field(0, description="Number of tasks currently running")
    tokens_spent_schema: int = Field(0, description="Tokens used by SchemaAgent")
    tokens_spent_data: int = Field(0, description="Tokens used by DataAgent")
    last_updated: datetime = Field(default_factory=datetime.utcnow)
