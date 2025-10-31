"""DataAgent orchestrating dataset generation with LangGraph."""
from __future__ import annotations

import logging
import json
from typing import Any, Awaitable, Callable, Dict, List, TypedDict

from langgraph.graph import END, StateGraph
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import get_settings
from app.models.schema import ColumnSpec, SchemaProposal
from app.services.agents.tools.deduplicate import DeduplicationTool
from app.services.generation.dataset_builder import DatasetBuilder
from app.services.generation.hybrid_numeric import HybridNumericGenerator
from app.utils.text import ensure_text

from .base import BaseAgent
from .llm_factory import build_gemini_chat

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], Awaitable[None]]


class GenerationState(TypedDict, total=False):
    task_id: str
    schema: SchemaProposal
    remaining_rows: int
    chunk_size: int
    rows: List[Dict[str, Any]]
    chunk_index: int
    use_hybrid_numeric: bool
    tokens_data: int
    chunk_rows: List[Dict[str, Any]]
    output_formats: List[str]
    output_files: Dict[str, str]
    last_reported_tokens: int
    progress_callback: ProgressCallback


class DataAgent(BaseAgent):
    """Generate dataset rows in chunks leveraging LangGraph state machine."""

    def __init__(self) -> None:
        settings = get_settings()
        llm = build_gemini_chat(model_name=settings.data_llm_model, temperature=0.3)
        super().__init__("data-agent", llm)
        self._parser = JsonOutputParser()
        self._prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                    You are DataAgent for SynthX.AI generating synthetic datasets.
                    Produce high-quality, diverse rows that respect the provided schema.
                    Respond only with JSON following the format instructions.
                    Avoid sensitive, offensive or real personal data.
                    """.strip(),
                ),
                (
                    "human",
                    """
                    Dataset schema:
                    {schema_json}

                    Rows already generated: {rows_generated}
                    Remaining rows to generate now: {rows_requested}

                    {format_instructions}
                    """.strip(),
                ),
            ]
        )
        self._dedupe_tool = DeduplicationTool()
        self._hybrid_generator = HybridNumericGenerator()
        self._settings = settings
        self._dataset_builder = DatasetBuilder(settings.generated_data_dir)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        graph: StateGraph = StateGraph(GenerationState)
        graph.add_node("generate_chunk", self._generate_chunk)
        graph.add_node("dedupe_chunk", self._dedupe_chunk)
        graph.add_node("finalise", self._finalise)
        graph.add_edge("generate_chunk", "dedupe_chunk")
        graph.add_conditional_edges(
            "dedupe_chunk",
            self._should_continue,
            {True: "generate_chunk", False: "finalise"},
        )
        graph.add_edge("finalise", END)
        graph.set_entry_point("generate_chunk")
        return graph.compile()

    async def generate_dataset(
        self,
        task_id: str,
        proposal: SchemaProposal,
        row_count: int,
        output_formats: List[str],
        use_hybrid_numeric: bool,
        progress_callback: ProgressCallback,
    ) -> GenerationState:
        state: GenerationState = GenerationState(
            task_id=task_id,
            schema=proposal,
            remaining_rows=row_count,
            chunk_size=min(self._settings.max_rows_per_chunk, row_count),
            rows=[],
            chunk_index=0,
            use_hybrid_numeric=use_hybrid_numeric,
            tokens_data=0,
            chunk_rows=[],
            output_formats=output_formats,
            progress_callback=progress_callback,
            last_reported_tokens=0,
        )
        result: GenerationState = await self._graph.ainvoke(state)
        result.setdefault("rows", [])
        return result

    async def _generate_chunk(self, state: GenerationState) -> GenerationState:
        requested = min(state["chunk_size"], state["remaining_rows"])
        if requested <= 0:
            state["chunk_rows"] = []
            return state

        schema = state["schema"]
        messages = self._prompt.format_messages(
            schema_json=json_dumps(schema),
            rows_generated=len(state["rows"]),
            rows_requested=requested,
            format_instructions=self._parser.get_format_instructions(),
        )
        response = await self.llm.ainvoke(messages)
        payload = self._parser.parse(ensure_text(response.content))
        rows = payload.get("rows") or payload
        if not isinstance(rows, list):
            raise ValueError("Generated rows payload must be a list")
        state["chunk_rows"] = rows
        state["remaining_rows"] = max(state["remaining_rows"] - len(rows), 0)
        usage = getattr(response, "usage_metadata", {}) or {}
        state["tokens_data"] += int(usage.get("total_tokens", 0))
        state["chunk_index"] = state.get("chunk_index", 0) + 1
        return state

    async def _dedupe_chunk(self, state: GenerationState) -> GenerationState:
        chunk_rows = state.get("chunk_rows", []) or []
        if not chunk_rows:
            return state
        filtered = await self._dedupe_tool.filter_new_rows(chunk_rows)
        duplicates_removed = len(chunk_rows) - len(filtered)
        if duplicates_removed > 0:
            state["remaining_rows"] = state.get("remaining_rows", 0) + duplicates_removed
        if state.get("use_hybrid_numeric"):
            hybrid = self._hybrid_generator.generate_chunk(
                columns=list(state["schema"].columns),
                row_count=len(filtered),
                offset=len(state["rows"]),
            )
            filtered = self._dataset_builder.merge_hybrid_values(filtered, hybrid)
        state.setdefault("rows", [])
        state["rows"].extend(filtered)
        progress_callback = state.get("progress_callback")
        if progress_callback and filtered:
            total_tokens = state.get("tokens_data", 0)
            last_tokens = state.get("last_reported_tokens", 0)
            delta = max(total_tokens - last_tokens, 0)
            state["last_reported_tokens"] = total_tokens
            await progress_callback(len(filtered), delta)
        state["chunk_rows"] = []
        return state

    async def _finalise(self, state: GenerationState) -> GenerationState:
        rows = state.get("rows", [])
        task_id = state["task_id"]
        outputs = self._dataset_builder.write_outputs(task_id, rows, state.get("output_formats", []))
        state["output_files"] = outputs
        return state

    def _should_continue(self, state: GenerationState) -> bool:
        return state.get("remaining_rows", 0) > 0

    async def ainvoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        result = await self.generate_dataset(
            task_id=state["task_id"],
            proposal=state["proposal"],
            row_count=state["row_count"],
            output_formats=state.get("output_formats", ["csv"]),
            use_hybrid_numeric=state.get("use_hybrid_numeric", False),
            progress_callback=state["progress_callback"],
        )
        state.update(result)
        return state


def json_dumps(proposal: SchemaProposal) -> str:
    columns: List[ColumnSpec] = list(proposal.columns)
    serialisable = {
        "title": proposal.title,
        "rationale": proposal.rationale,
    "columns": [col.model_dump() for col in columns],
    }
    return json.dumps(serialisable, indent=2)
