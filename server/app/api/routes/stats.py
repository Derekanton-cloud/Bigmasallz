"""Live statistics endpoint for frontend dashboard."""
from __future__ import annotations

from fastapi import APIRouter

from app.models.stats import LiveStats
from app.services.stats_service import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/live", response_model=LiveStats)
async def live_stats() -> LiveStats:
    return await stats_service.snapshot()
