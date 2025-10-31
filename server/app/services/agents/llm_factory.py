"""Factory utilities for constructing LangChain LLM clients."""
from __future__ import annotations

import logging
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def build_gemini_chat(model_name: str, temperature: float = 0.2, **kwargs: Any) -> BaseChatModel:
    """Return a configured Gemini chat model for LangChain usage."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. Please set it in the environment before running SynthX.AI backend."
        )

    logger.debug("Initialising Gemini chat model %s", model_name)
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=settings.gemini_api_key,
        **kwargs,
    )
