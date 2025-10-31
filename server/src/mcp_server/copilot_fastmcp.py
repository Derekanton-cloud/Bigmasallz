"""FastMCP server that powers dataset generation via GitHub Copilot (Claude Sonnet)."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel, Field, conint

from src.core.models import OutputFormat, StorageType
from src.services.generation_service import get_generation_service
from src.utils.logger import get_logger

logger = get_logger(__name__)

app = FastMCP("copilot-dataset-generator")


class GenerateDatasetInput(BaseModel):
    """Payload for the generate_dataset tool."""

    schema: dict[str, Any] = Field(..., description="Data schema describing the dataset to generate")
    total_rows: conint(gt=0) = Field(..., description="Total number of rows to generate")
    chunk_size: conint(gt=0) | None = Field(None, description="Optional chunk size for generation")
    output_format: OutputFormat = Field(OutputFormat.CSV, description="Desired output format")
    storage_type: StorageType = Field(StorageType.MEMORY, description="Storage backend to use")
    seed: int | None = Field(None, description="Optional random seed for deterministic output")
    include_rows: bool = Field(
        False,
        description="If true, include generated rows directly in the tool response (may be large).",
    )


@app.tool(name="generate_dataset", description="Generate a dataset using GitHub Copilot (Claude Sonnet).")
async def generate_dataset(payload: GenerateDatasetInput) -> dict[str, Any]:
    """Generate dataset using the configured generation service."""
    service = get_generation_service()

    if service.provider != "copilot":
        raise RuntimeError(
            "Generation service is not configured for Copilot. Set GENERATION_PROVIDER=copilot before starting the server."
        )

    # Create job
    job_state = service.create_generation_job(
        schema=payload.schema,
        total_rows=payload.total_rows,
        chunk_size=payload.chunk_size,
        output_format=payload.output_format,
        storage_type=payload.storage_type,
        seed=payload.seed,
    )

    rows: list[dict[str, Any]] = []
    for chunk_index in range(1, job_state.progress.total_chunks + 1):
        response = service.generate_chunk(
            job_id=job_state.specification.job_id,
            chunk_id=chunk_index,
        )
        if payload.include_rows:
            rows.extend(response.data)

    download = service.merge_job_dataset(job_state.specification.job_id)

    result: dict[str, Any] = {
        "job_id": str(job_state.specification.job_id),
        "total_rows": job_state.progress.rows_generated,
        "chunk_size": job_state.specification.chunk_size,
        "chunks_completed": job_state.progress.chunks_completed,
        "output_format": job_state.specification.output_format.value,
        "storage_path": download.file_path,
        "download_url": download.download_url,
    }

    if payload.include_rows:
        result["rows"] = rows

    return result


def main():
    """Entrypoint for launching the FastMCP server."""
    logger.info("Starting FastMCP Copilot dataset server")
    app.run()


if __name__ == "__main__":
    main()
