"""Dataset generation models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .schema import SchemaProposal


class DatasetTaskStatus(str, Enum):
    """Lifecycle states for dataset generation task."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DatasetGenerationRequest(BaseModel):
    """Request payload for initiating dataset generation."""

    proposal: SchemaProposal
    row_count: int = Field(..., gt=0)
    output_formats: List[str] = Field(default_factory=lambda: ["csv"])
    use_hybrid_numeric: bool = Field(False)


class DatasetGenerationTask(BaseModel):
    """Internal task representation tracked by TaskManager."""

    task_id: str
    status: DatasetTaskStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    progress_rows: int = 0
    total_rows: int = 0
    error_message: Optional[str] = None
    output_files: Dict[str, str] = Field(default_factory=dict)
    tokens_schema: int = 0
    tokens_data: int = 0


class DatasetGenerationResponse(BaseModel):
    """API response when a dataset generation task is queued."""

    task_id: str
    status: DatasetTaskStatus


class DatasetStatusResponse(BaseModel):
    """API response summarising task progress."""

    task_id: str
    status: DatasetTaskStatus
    progress_rows: int
    total_rows: int
    output_files: Dict[str, str]
    error_message: Optional[str] = None
    tokens_schema: int = 0
    tokens_data: int = 0
