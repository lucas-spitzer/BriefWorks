from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Importance = Literal["essential", "supporting", "contextual"]


class DeconstructedConcept(BaseModel):
    term_label: str
    definition: str
    aliases: list[str] = Field(default_factory=list)
    prerequisite_labels: list[str] = Field(default_factory=list)
    pronunciation: str | None = None
    importance: Importance = "supporting"
    evidence_segment_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentDeconstructorOutput(BaseModel):
    concepts: list[DeconstructedConcept]
