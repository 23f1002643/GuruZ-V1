from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    field: str
    message: str


class ValidationReport(BaseModel):
    is_valid: bool = False
    overall_score: float = 0.0
    hallucination_score: float = 0.0
    completeness_score: float = 0.0
    json_validity_score: float = 0.0
    educational_quality_score: float = 0.0
    consistency_score: float = 0.0
    schema_valid: bool = False
    all_objectives_covered: bool = False
    source_chunks_verified: bool = False
    issues: list[ValidationIssue] = Field(default_factory=list)
    regeneration_count: int = 0
