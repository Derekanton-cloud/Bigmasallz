"""Lifecycle event hooks for FastAPI application."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.repositories.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def register_event_handlers(app: FastAPI) -> None:
    """Attach startup and shutdown handlers to the FastAPI instance."""

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Starting SynthX.AI backend application")
        await get_vector_store().ainit()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Shutting down SynthX.AI backend application")
        await get_vector_store().aclose()
