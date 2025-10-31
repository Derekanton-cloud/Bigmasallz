"""Base abstractions shared by SynthX.AI agents."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from langchain_core.language_models.chat_models import BaseChatModel

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Common contract for agent implementations."""

    def __init__(self, name: str, llm: BaseChatModel) -> None:
        self.name = name
        self._llm = llm

    @property
    def llm(self) -> BaseChatModel:
        return self._llm

    @abstractmethod
    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic and return updated state."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
