"""Pydantic models used for schema generation endpoints."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ColumnSpec(BaseModel):
    """Describe a single column produced by SchemaAgent."""

    name: str = Field(..., description="Canonical column name")
    data_type: str = Field(..., description="Semantic data type for the column")
    description: str = Field(..., description="Human readable meaning of the column")
    constraints: List[str] = Field(
        default_factory=list, description="Additional validation constraints"
    )
    example: Optional[str] = Field(
        default=None, description="Example value that matches the column definition"
    )


class SchemaProposal(BaseModel):
    """Container for proposed dataset schema."""

    title: Optional[str] = Field(
        default=None,
        description="Short title describing the dataset",
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Explanation of how the schema matches the user prompt",
    )
    columns: List[ColumnSpec] = Field(
        default_factory=list,
        description="Ordered set of columns for the dataset",
    )


class SchemaPrompt(BaseModel):
    """Incoming prompt used to propose a schema."""

    prompt: str = Field(..., description="Natural language description of dataset needs")


class SchemaProposalResponse(BaseModel):
    """Response payload containing schema proposal."""

    proposal: SchemaProposal


class SchemaApprovalRequest(BaseModel):
    """Payload used when user confirms schema and requests dataset generation."""

    proposal: SchemaProposal
    row_count: int = Field(..., gt=0, description="Desired number of rows")
    output_formats: List[str] = Field(
        default_factory=lambda: ["csv"],
        description="Desired output formats (csv, json)",
    )
    use_hybrid_numeric: bool = Field(
        False,
        description="Enable deterministic numeric generation for cost savings",
    )
