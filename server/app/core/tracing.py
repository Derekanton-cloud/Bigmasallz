"""Optional LangSmith tracing configuration."""
from __future__ import annotations

import os
from typing import Optional

from app.core.config import Settings


def configure_tracing(settings: Settings) -> None:
    """Enable LangSmith tracing when credentials are available."""
    api_key: Optional[str] = settings.langsmith_api_key
    if not api_key:
        return
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", api_key)
    if settings.langsmith_project:
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
