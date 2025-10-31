"""Utility helpers for working with LLM message payloads."""
from __future__ import annotations

from typing import Any, Iterable


def ensure_text(content: Any) -> str:
    """Normalise LLM message content into a usable string."""
    if isinstance(content, str):
        return content
    if isinstance(content, Iterable):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)
