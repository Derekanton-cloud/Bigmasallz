"""Client for interacting with GitHub Copilot (Claude Sonnet) for dataset generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx
from json_repair import repair_json
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.core.models import (
    DataSchema,
    FieldConstraint,
    FieldDefinition,
    FieldType,
    SchemaExtractionRequest,
    SchemaExtractionResponse,
)
from src.services.fallback_generator import build_fallback_generator
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CopilotConfigurationError(RuntimeError):
    """Raised when Copilot configuration is missing."""


class CopilotAPIError(RuntimeError):
    """Raised when the Copilot API reports an error."""


@dataclass
class _CopilotSettings:
    api_key: str
    model: str
    base_url: str | None
    temperature: float
    timeout: int
    max_retries: int
    max_rows_per_call: int


class CopilotClient:
    """GitHub Copilot API client for schema and dataset generation."""

    DEFAULT_SYSTEM_PROMPT: ClassVar[str] = (
        "You are an expert synthetic data generator. "
        "Return strictly valid JSON that matches the requested schema. "
        "Never include explanations or Markdown fences."
    )

    def __init__(self, client: httpx.Client | None = None):
        config = settings.copilot
        if not config:
            raise CopilotConfigurationError(
                "Copilot configuration missing. Ensure COPILOT_API_KEY is set."
            )

        self._settings = _CopilotSettings(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
            timeout=config.timeout,
            max_retries=config.max_retries,
            max_rows_per_call=config.max_rows_per_call,
        )

        headers = {
            "Authorization": f"Bearer {self._settings.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "synthetic-data-generator/fastmcp",
        }

        base_url = self._settings.base_url or "https://api.githubcopilot.com/v1"
        timeout = httpx.Timeout(self._settings.timeout)
        self._client = client or httpx.Client(base_url=base_url, headers=headers, timeout=timeout)
        self._fallback = build_fallback_generator()

    def _messages(self, system_prompt: str, user_prompt: str) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            logger.error("Copilot request failed: %s", exc, exc_info=True)
            raise CopilotAPIError(str(exc)) from exc

    def _extract_json(self, content: str) -> Any:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            repaired = repair_json(text)
            return json.loads(repaired)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    def _invoke(self, *, system_prompt: str, user_prompt: str, response_schemas: dict[str, Any] | None = None) -> Any:
        messages = self._messages(system_prompt, user_prompt)
        payload: dict[str, Any] = {
            "model": self._settings.model,
            "messages": messages,
            "temperature": self._settings.temperature,
        }
        if response_schemas:
            payload["response_format"] = response_schemas

        logger.debug("Calling Copilot with model %s", self._settings.model)
        data = self._post(payload)

        choices = data.get("choices")
        if not choices:
            raise CopilotAPIError("Copilot returned no choices")

        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise CopilotAPIError("Copilot response missing content")

        if isinstance(content, list):
            # Some APIs may return structured content blocks
            content_text = "".join(block.get("text", "") for block in content)
        else:
            content_text = str(content)

        return self._extract_json(content_text)

    def extract_schema(self, request: SchemaExtractionRequest) -> SchemaExtractionResponse:
        logger.info("Extracting schema with Copilot")
        system_prompt = (
            "You convert natural language dataset descriptions into structured JSON schemas. "
            "Output JSON with fields, constraints, and suggestions."
        )
        user_prompt = self._build_schema_prompt(request)

        try:
            response = self._invoke(system_prompt=system_prompt, user_prompt=user_prompt)
        except CopilotAPIError as exc:
            logger.warning("Copilot schema extraction failed, using fallback: %s", exc)
            return self._fallback.extract_schema(request)

        return self._parse_schema_response(response)

    def generate_data_chunk(
        self,
        *,
        schema: DataSchema,
        num_rows: int,
        existing_values: dict[str, list[Any]] | None = None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Generate dataset rows matching the schema."""
        effective_rows = min(num_rows, self._settings.max_rows_per_call)
        if num_rows > self._settings.max_rows_per_call:
            logger.debug(
                "Copilot request truncated to %s rows (requested %s)",
                effective_rows,
                num_rows,
            )

        system_prompt = self.DEFAULT_SYSTEM_PROMPT
        user_prompt = self._build_generation_prompt(
            schema=schema,
            num_rows=effective_rows,
            existing_values=existing_values,
            seed=seed,
        )

        try:
            data = self._invoke(system_prompt=system_prompt, user_prompt=user_prompt)
        except CopilotAPIError as exc:
            logger.warning("Copilot generation failed, using fallback: %s", exc)
            return self._fallback.generate_data_chunk(
                schema=schema,
                num_rows=effective_rows,
                existing_values=existing_values,
                seed=seed,
            )

        if not isinstance(data, list):
            raise CopilotAPIError("Copilot response was not a JSON array")

        return [self._coerce_row(schema, row) for row in data][:effective_rows]

    def max_rows_per_call(self) -> int:
        return self._settings.max_rows_per_call

    def _build_schema_prompt(self, request: SchemaExtractionRequest) -> str:
        context_lines = []
        context_lines.append(f"Dataset description: {request.user_input}")
        if request.context:
            context_lines.append(f"Context: {json.dumps(request.context, indent=2)}")
        if request.example_data:
            context_lines.append("Example data snippet:\n" + request.example_data[:1000])

        instructions = (
            "Return JSON with keys: fields (list), description, suggestions (list of strings), "
            "warnings (list of strings), confidence (float). Each field should contain name, type, "
            "description, constraints (unique, nullable, min_value, max_value, pattern, enum_values), "
            "sample_values, depends_on, generation_hint."
        )
        return "\n\n".join(context_lines + [instructions])

    def _parse_schema_response(self, payload: dict[str, Any]) -> SchemaExtractionResponse:
        fields_data = payload.get("fields", [])
        fields: list[FieldDefinition] = []
        for field_data in fields_data:
            constraints_raw = field_data.get("constraints", {})
            constraint = FieldConstraint(
                unique=constraints_raw.get("unique", False),
                nullable=constraints_raw.get("nullable", True),
                min_value=constraints_raw.get("min_value"),
                max_value=constraints_raw.get("max_value"),
                min_length=constraints_raw.get("min_length"),
                max_length=constraints_raw.get("max_length"),
                pattern=constraints_raw.get("pattern"),
                enum_values=constraints_raw.get("enum_values"),
                format=constraints_raw.get("format"),
                default=constraints_raw.get("default"),
            )
            depends_on = field_data.get("depends_on")
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            elif depends_on is None:
                depends_on = None

            field_type_value = str(field_data.get("type", "string")).lower()
            try:
                field_type = FieldType(field_type_value)
            except ValueError:
                field_type = FieldType.STRING

            fields.append(
                FieldDefinition(
                    name=field_data["name"],
                    type=field_type,
                    description=field_data.get("description"),
                    constraints=constraint,
                    sample_values=field_data.get("sample_values", []),
                    depends_on=depends_on,
                    generation_hint=field_data.get("generation_hint"),
                )
            )

        schema = DataSchema(
            fields=fields,
            description=payload.get("description"),
            relationships=payload.get("relationships"),
            metadata=payload.get("metadata", {}),
        )

        return SchemaExtractionResponse(
            schema=schema,
            confidence=float(payload.get("confidence", 0.75)),
            suggestions=payload.get("suggestions", []),
            warnings=payload.get("warnings", []),
        )

    def _build_generation_prompt(
        self,
        *,
        schema: DataSchema,
        num_rows: int,
        existing_values: dict[str, list[Any]] | None,
        seed: int | None,
    ) -> str:
        schema_description = {
            "fields": [
                {
                    "name": field.name,
                    "type": field.type.value,
                    "constraints": field.constraints.model_dump(mode="json"),
                    "sample_values": field.sample_values,
                    "generation_hint": field.generation_hint,
                }
                for field in schema.fields
            ],
            "description": schema.description,
        }

        parts = [
            f"Generate {num_rows} rows that strictly follow this schema.",
            json.dumps(schema_description, indent=2),
            "Return a JSON array where each element is an object with exactly the schema's fields.",
        ]

        if existing_values:
            parts.append(
                "Avoid reusing these existing values for uniqueness fields: "
                + json.dumps(existing_values, indent=2)
            )
        if seed is not None:
            parts.append(f"Use seed {seed} for deterministic ordering when possible.")

        return "\n\n".join(parts)

    def _coerce_row(self, schema: DataSchema, row: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(row, dict):
            raise CopilotAPIError("Copilot returned a non-object row")

        normalized: dict[str, Any] = {}
        for field in schema.fields:
            value = row.get(field.name)
            if value is None and field.constraints.default is not None:
                value = field.constraints.default
            normalized[field.name] = value
        return normalized


_copilot_singleton: CopilotClient | None = None


def get_copilot_client() -> CopilotClient:
    """Retrieve singleton Copilot client."""
    global _copilot_singleton
    if _copilot_singleton is None:
        _copilot_singleton = CopilotClient()
    return _copilot_singleton
