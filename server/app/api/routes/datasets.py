"""Endpoints for dataset generation lifecycle."""
from __future__ import annotations

import asyncio
from uuid import uuid4

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import get_orchestrator, get_task_manager
from app.models.dataset import (
    DatasetGenerationRequest,
    DatasetGenerationResponse,
    DatasetGenerationTask,
    DatasetStatusResponse,
    DatasetTaskStatus,
)
from app.services.agents.orchestrator import AgentsOrchestrator
from app.services.task_manager import TaskManager

router = APIRouter(prefix="/datasets", tags=["datasets"])

ALLOWED_FORMATS = {"csv", "json"}


@router.post("/generate", response_model=DatasetGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_dataset(
    payload: DatasetGenerationRequest,
    orchestrator: AgentsOrchestrator = Depends(get_orchestrator),
    task_manager: TaskManager = Depends(get_task_manager),
    background_tasks: BackgroundTasks | None = None,
) -> DatasetGenerationResponse:
    invalid = set(fmt.lower() for fmt in payload.output_formats) - ALLOWED_FORMATS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported output formats: {', '.join(invalid)}",
        )

    task_id = uuid4().hex
    dataset_task = DatasetGenerationTask(task_id=task_id, status=DatasetTaskStatus.QUEUED)
    response = await task_manager.create_task(dataset_task)

    async def runner() -> None:
        try:
            await task_manager.mark_running(task_id, payload)

            async def progress_callback(rows: int, tokens: int) -> None:
                await task_manager.mark_progress(task_id, rows, tokens_data=tokens)

            result = await orchestrator.generate_dataset(
                task_id=task_id,
                request=payload,
                progress_callback=progress_callback,
            )
            await task_manager.mark_succeeded(task_id, result.get("output_files", {}))
        except Exception as exc:  # noqa: BLE001
            await task_manager.mark_failed(task_id, str(exc))

    if background_tasks is not None:
        background_tasks.add_task(runner)
    else:
        asyncio.create_task(runner())

    return response


@router.get("/{task_id}/status", response_model=DatasetStatusResponse)
async def dataset_status(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
) -> DatasetStatusResponse:
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return DatasetStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress_rows=task.progress_rows,
        total_rows=task.total_rows,
        output_files=task.output_files,
        error_message=task.error_message,
        tokens_schema=task.tokens_schema,
        tokens_data=task.tokens_data,
    )


@router.get("/{task_id}/download")
async def download_dataset(
    task_id: str,
    format: str = Query("csv", regex="^(csv|json)$"),
    task_manager: TaskManager = Depends(get_task_manager),
) -> FileResponse:
    task = await task_manager.get_task(task_id)
    if not task or task.status != DatasetTaskStatus.SUCCEEDED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not ready")
    file_path = task.output_files.get(format)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requested format not available")
    resolved = Path(file_path)
    if not resolved.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on server")
    return FileResponse(path=str(resolved), filename=resolved.name)
