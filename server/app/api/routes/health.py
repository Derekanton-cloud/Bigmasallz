"""Health endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ping")
async def ping() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name}
