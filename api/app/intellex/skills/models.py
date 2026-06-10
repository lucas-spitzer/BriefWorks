from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DocumentType = Literal[
    "military_doctrine",
    "research_paper",
    "white_paper",
    "report",
    "unknown",
]


class SourceResearchOutput(BaseModel):
    document_type: DocumentType
    title: str
    identifier: str | None = None
    issuing_authority: str | None = None
    authors: list[str] = Field(default_factory=list)
    version: str | None = None
    publication_date_in_document: str | None = None
    publication_date_public: str | None = None
    source_url: str | None = None
    abstract: str | None = None
    confidence: dict[str, float] = Field(default_factory=dict)
    provenance: dict[str, Literal["document", "web", "inferred"]] = Field(default_factory=dict)
    web_sources: list[dict[str, str]] = Field(default_factory=list)

    def to_metadata(self, *, researched_at: str) -> dict[str, Any]:
        return {
            **self.model_dump(),
            "researched_at": researched_at,
        }
