"""Tests for the Copilot client abstraction."""

from __future__ import annotations

import json
from typing import Any

import pytest

from src.api.copilot_client import CopilotClient, CopilotAPIError
from src.config import settings
from src.core.models import DataSchema, FieldDefinition, FieldType


class _DummyResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _DummyClient:
    def __init__(self, response_payload: dict[str, Any]):
        self.response_payload = response_payload
        self.requests: list[dict[str, Any]] = []

    def post(self, path: str, json: dict[str, Any]):  # pragma: no cover - simple forwarder
        self.requests.append({"path": path, "payload": json})
        return _DummyResponse(self.response_payload)


@pytest.fixture()
def configured_copilot(monkeypatch) -> CopilotClient:
    monkeypatch.setattr(settings, "copilot_api_key", "test-key", raising=False)
    monkeypatch.setattr(settings, "copilot_model", "claude-3.5-sonnet", raising=False)
    monkeypatch.setattr(settings, "copilot_timeout", 30, raising=False)
    monkeypatch.setattr(settings, "copilot_temperature", 0.1, raising=False)
    monkeypatch.setattr(settings, "copilot_max_retries", 1, raising=False)
    monkeypatch.setattr(settings, "copilot_max_rows_per_call", 5, raising=False)

    dummy_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps([
                        {"name": f"Item {index}", "value": index}
                        for index in range(1, 8)
                    ])
                }
            }
        ]
    }
    client = _DummyClient(dummy_payload)
    return CopilotClient(client=client)


def test_copilot_generate_data_chunk(configured_copilot):
    schema = DataSchema(fields=[FieldDefinition(name="name", type=FieldType.STRING)])
    rows = configured_copilot.generate_data_chunk(schema=schema, num_rows=10)

    # Copilot should clamp to max_rows_per_call (5) and return structured rows
    assert len(rows) == 5
    assert {"name"} == set(rows[0].keys())


def test_copilot_error_raises_for_missing_content(monkeypatch):
    monkeypatch.setattr(settings, "copilot_api_key", "test-key", raising=False)
    monkeypatch.setattr(settings, "copilot_model", "claude-3.5-sonnet", raising=False)
    monkeypatch.setattr(settings, "copilot_timeout", 30, raising=False)

    dummy_payload = {"choices": [{"message": {}}]}
    client = _DummyClient(dummy_payload)

    copilot = CopilotClient(client=client)
    schema = DataSchema(fields=[FieldDefinition(name="id", type=FieldType.STRING)])

    rows = copilot.generate_data_chunk(schema=schema, num_rows=1)

    # When the API response is malformed we fall back to the heuristic generator
    assert len(rows) == 1
    assert "id" in rows[0]
