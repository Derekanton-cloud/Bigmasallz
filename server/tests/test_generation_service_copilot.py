"""Tests for GenerationService when using the Copilot provider."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any
import pytest

from src.config import settings
from src.core.models import (
    DataSchema,
    FieldConstraint,
    FieldDefinition,
    FieldType,
    JobSpecification,
    OutputFormat,
    StorageType,
)
from src.services import generation_service as gs_module


class StubCopilotClient:
    def __init__(self, max_rows: int = 3):
        self.max_rows = max_rows
        self.calls: list[int] = []

    def max_rows_per_call(self) -> int:
        return self.max_rows

    def generate_data_chunk(
        self,
        *,
        schema: DataSchema,
        num_rows: int,
        existing_values: dict[str, list[Any]] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append(num_rows)
        rows_to_return = min(num_rows, self.max_rows)
        return [
            {field.name: f"{field.name}-{len(self.calls)}-{idx}" for field in schema.fields}
            for idx in range(rows_to_return)
        ]


@pytest.fixture()
def copilot_service(monkeypatch):
    temp_dir = tempfile.mkdtemp()

    monkeypatch.setattr(settings, "generation_provider", "copilot", raising=False)
    monkeypatch.setattr(settings, "copilot_api_key", "test-key", raising=False)
    monkeypatch.setattr(settings, "copilot_model", "claude-3.5-sonnet", raising=False)
    monkeypatch.setattr(settings, "copilot_timeout", 30, raising=False)
    monkeypatch.setattr(settings, "copilot_max_rows_per_call", 3, raising=False)
    monkeypatch.setattr(settings, "default_chunk_size", 9, raising=False)
    monkeypatch.setattr(settings, "job_persistence_path", str(Path(temp_dir) / "jobs"), raising=False)
    monkeypatch.setattr(settings, "storage_type", "memory", raising=False)

    stub_client = StubCopilotClient(max_rows=3)

    monkeypatch.setattr(gs_module, "_generation_service", None)
    monkeypatch.setattr(gs_module, "get_copilot_client", lambda: stub_client)

    import src.core.job_manager as jm_module

    monkeypatch.setattr(jm_module, "_job_manager", None)
    monkeypatch.setattr(jm_module.settings, "job_persistence_path", Path(temp_dir) / "jobs", raising=False)

    service = gs_module.GenerationService()
    service.job_manager.jobs.clear()
    return service, stub_client


def test_generate_chunk_uses_sub_batches(copilot_service):
    service, stub_client = copilot_service

    schema = DataSchema(
        fields=[
            FieldDefinition(
                name="item",
                type=FieldType.STRING,
                constraints=FieldConstraint(unique=False, nullable=False),
            )
        ]
    )

    specification = JobSpecification(
        schema=schema,
        total_rows=9,
        chunk_size=9,
        output_format=OutputFormat.JSON,
        storage_type=StorageType.MEMORY,
    )

    job_state = service.job_manager.create_job(specification)
    service.job_manager.validate_schema(job_state.specification.job_id)
    job_state.schema_validated = True

    response = service.generate_chunk(job_id=job_state.specification.job_id, chunk_id=1)

    assert response.rows_generated == 9
    assert stub_client.calls == [9, 6, 3]
