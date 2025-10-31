"""High level coordination between SchemaAgent and DataAgent."""
from __future__ import annotations

from typing import Awaitable, Callable, Dict

from app.models.dataset import DatasetGenerationRequest
from app.models.schema import SchemaProposal

from .data_agent import DataAgent
from .schema_agent import SchemaAgent


class AgentsOrchestrator:
    """Facade that exposes key workflows to the API layer."""

    def __init__(self) -> None:
        self._schema_agent = SchemaAgent()
        self._data_agent = DataAgent()

    async def propose_schema(self, prompt: str) -> tuple[SchemaProposal, int]:
        return await self._schema_agent.propose_schema(prompt)

    async def generate_dataset(
        self,
        task_id: str,
        request: DatasetGenerationRequest,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> Dict[str, object]:
        state = await self._data_agent.generate_dataset(
            task_id=task_id,
            proposal=request.proposal,
            row_count=request.row_count,
            output_formats=request.output_formats,
            use_hybrid_numeric=request.use_hybrid_numeric,
            progress_callback=progress_callback,
        )
        return state


orchestrator = AgentsOrchestrator()
