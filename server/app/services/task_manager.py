"""In-memory task manager coordinating dataset generation lifecycle."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Optional

from app.models.dataset import (
    DatasetGenerationRequest,
    DatasetGenerationResponse,
    DatasetGenerationTask,
    DatasetTaskStatus,
)
from app.services.stats_service import stats_service


class TaskManager:
    """Track dataset generation tasks and provide thread-safe operations."""

    def __init__(self) -> None:
        self._tasks: Dict[str, DatasetGenerationTask] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task: DatasetGenerationTask) -> DatasetGenerationResponse:
        async with self._lock:
            self._tasks[task.task_id] = task
        await stats_service.track_task_created()
        return DatasetGenerationResponse(task_id=task.task_id, status=task.status)

    async def mark_running(self, task_id: str, request: DatasetGenerationRequest) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = DatasetTaskStatus.RUNNING
            task.total_rows = request.row_count
            task.updated_at = datetime.utcnow()
            self._tasks[task_id] = task
        await stats_service.track_task_running()

    async def mark_progress(
        self,
        task_id: str,
        increment: int,
        tokens_schema: int = 0,
        tokens_data: int = 0,
    ) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.progress_rows += increment
            task.tokens_schema += tokens_schema
            task.tokens_data += tokens_data
            task.updated_at = datetime.utcnow()
            self._tasks[task_id] = task
        await stats_service.track_rows_generated(increment)
        if tokens_schema:
            await stats_service.track_schema_tokens(tokens_schema)
        if tokens_data:
            await stats_service.track_data_tokens(tokens_data)

    async def mark_succeeded(self, task_id: str, output_files: Dict[str, str]) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = DatasetTaskStatus.SUCCEEDED
            task.output_files = output_files
            task.updated_at = datetime.utcnow()
            self._tasks[task_id] = task
        await stats_service.track_task_completed()

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        async with self._lock:
            task = self._tasks[task_id]
            task.status = DatasetTaskStatus.FAILED
            task.error_message = error_message
            task.updated_at = datetime.utcnow()
            self._tasks[task_id] = task
        await stats_service.track_task_failed()

    async def get_task(self, task_id: str) -> Optional[DatasetGenerationTask]:
        async with self._lock:
            return self._tasks.get(task_id)


task_manager = TaskManager()
