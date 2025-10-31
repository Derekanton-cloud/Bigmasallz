"""FastAPI dependencies for SynthX.AI endpoints."""
from __future__ import annotations

from app.core.config import get_settings
from app.services.agents.orchestrator import orchestrator
from app.services.task_manager import task_manager


def get_app_settings():
    return get_settings()


def get_orchestrator():
    return orchestrator


def get_task_manager():
    return task_manager
