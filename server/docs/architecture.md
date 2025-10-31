# SynthX.AI Backend Architecture

## Overview

SynthX.AI is a production-ready FastAPI backend that orchestrates two LangChain agents—SchemaAgent and DataAgent—to transform natural language prompts into fully realised synthetic datasets. The platform embraces asynchronous execution, traceability via LangSmith, and deduplication through ChromaDB.

## Key Components

- **FastAPI Application (`app/main.py`)**: Exposes RESTful APIs for schema proposal, dataset generation, health probing, and live stats.
- **Settings & Logging (`app/core`)**: Centralised configuration via `pydantic-settings`, structured logging, and optional LangSmith tracing hooks.
- **Agents (`app/services/agents`)**:
  - *SchemaAgent*: Calls Gemini (1.5 Pro) to derive column definitions, constraints, and rationale from prompts.
  - *DataAgent*: Uses LangGraph to iterate chunked dataset creation, optional hybrid numeric generation, and MCP deduplication with ChromaDB.
- **Task Manager (`app/services/task_manager.py`)**: Tracks asynchronous dataset generation progress and exposure of task status.
- **Stats Service (`app/services/stats_service.py`)**: Maintains live metrics used by the frontend dashboard.
- **Generation Utilities (`app/services/generation`)**: Hybrid numeric helpers and dataset persistence functions.
- **Vector Store (`app/repositories/vector_store.py`)**: Wraps ChromaDB HTTP client for deduplication.

## Data Flow

1. User submits prompt → `SchemaAgent` returns schema proposal.
2. User confirms schema + row count → dataset task queued (`TaskManager`).
3. Background coroutine executes LangGraph pipeline, chunking LLM requests and augmenting with hybrid numeric values where applicable.
4. Deduplication tool persists row hashes into ChromaDB to avoid duplicates.
5. `DatasetBuilder` persists CSV/JSON files to `/generated`; task status updated.
6. Live stats service aggregates rows generated and token usage, powering frontend telemetry.

## Deployment

- Dockerfile leverages `python:3.11-slim`; compose stack adds ChromaDB and the Next.js client.
- `.env` + `.env.example` illustrate runtime configuration with Gemini and LangSmith credentials.
- Volumes mount `logs/` and `generated/` ensuring host visibility.
