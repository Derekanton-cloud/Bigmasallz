"""Common API models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Error payload returned by API."""

    detail: str = Field(..., description="Error description")
