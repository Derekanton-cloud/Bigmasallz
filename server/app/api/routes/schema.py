"""Schema generation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_orchestrator
from app.models.schema import SchemaPrompt, SchemaProposalResponse
from app.services.agents.orchestrator import AgentsOrchestrator
from app.services.stats_service import stats_service

router = APIRouter(prefix="/schema", tags=["schema"])


@router.post("/propose", response_model=SchemaProposalResponse, status_code=status.HTTP_201_CREATED)
async def propose_schema(
    payload: SchemaPrompt,
    orchestrator: AgentsOrchestrator = Depends(get_orchestrator),
) -> SchemaProposalResponse:
    try:
        proposal, tokens = await orchestrator.propose_schema(payload.prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    await stats_service.track_schema_tokens(tokens)
    return SchemaProposalResponse(proposal=proposal)
