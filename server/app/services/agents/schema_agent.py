"""SchemaAgent powered by Gemini for schema generation."""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.models.schema import SchemaProposal

from .base import BaseAgent
from .llm_factory import build_gemini_chat

logger = logging.getLogger(__name__)


class SchemaAgent(BaseAgent):
    """Generate dataset schemas based on natural language prompts."""

    def __init__(self) -> None:
        settings = get_settings()
        llm = build_gemini_chat(model_name=settings.schema_llm_model, temperature=0.1)
        super().__init__("schema-agent", llm)
        self._parser = JsonOutputParser(pydantic_object=SchemaProposal)
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    You are SchemaAgent, a meticulous data architect for SynthX.AI.
                    You transform user prompts into dataset schemas optimised for synthetic data generation.
                    Always return valid JSON matching the given format instructions.
                    Each column must include name, data_type, description. Provide meaningful constraints when applicable.
                    Limit to 30 columns.
                    """.strip(),
                ),
                (
                    "human",
                    """
                    User prompt: {user_prompt}

                    {format_instructions}
                    """.strip(),
                ),
            ]
        )

    async def propose_schema(self, prompt: str) -> Tuple[SchemaProposal, int]:
        """Call Gemini model to propose a dataset schema."""
        messages = self._prompt.format_messages(
            user_prompt=prompt,
            format_instructions=self._parser.get_format_instructions(),
        )
        response = await self.llm.ainvoke(messages)
        payload = self._parse_response(response.content)
        schema = SchemaProposal.model_validate(payload)
        usage = getattr(response, "usage_metadata", {}) or {}
        total_tokens = int(usage.get("total_tokens", 0))
        logger.info("Schema generated with %d columns", len(schema.columns))
        return schema, total_tokens

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        prompt = state.get("prompt")
        if not prompt:
            raise ValueError("State missing user prompt for SchemaAgent")
        schema, tokens = await self.propose_schema(prompt)
        state.update({"proposal": schema, "tokens_schema": tokens})
        return state

    def _parse_response(self, content: Any) -> Dict[str, Any]:
        if isinstance(content, str):
            text = content
        else:
            text = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        try:
            return self._parser.parse(text)
        except Exception:
            logger.exception("Failed to parse schema JSON. Raw response: %s", text)
            raise
