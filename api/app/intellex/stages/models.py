from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

DocumentType = Literal[
    "military_doctrine",
    "research_paper",
    "white_paper",
    "report",
    "unknown",
]

_DOCUMENT_TYPES = {
    "military_doctrine",
    "research_paper",
    "white_paper",
    "report",
    "unknown",
}
_PROVENANCE_VALUES = {"document", "web", "inferred"}


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
    distribution_line: str | None = None

    # Coerce messy LLM output before failing the run.

    @field_validator("document_type", mode="before")
    @classmethod
    def _coerce_document_type(cls, value: Any) -> str:
        if isinstance(value, str) and value in _DOCUMENT_TYPES:
            return value
        return "unknown"

    @field_validator("title", mode="before")
    @classmethod
    def _coerce_title(cls, value: Any) -> str:
        if isinstance(value, str) and value.strip():
            return value
        return "Untitled document"

    @field_validator("authors", mode="before")
    @classmethod
    def _coerce_authors(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        return []

    @field_validator("web_sources", mode="before")
    @classmethod
    def _coerce_web_sources(cls, value: Any) -> list:
        if isinstance(value, list):
            return value
        return []

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: Any) -> dict:
        if not isinstance(value, dict):
            return {}
        cleaned: dict[str, float] = {}
        for key, raw in value.items():
            try:
                cleaned[str(key)] = float(raw)
            except (TypeError, ValueError):
                continue
        return cleaned

    @field_validator("provenance", mode="before")
    @classmethod
    def _coerce_provenance(cls, value: Any) -> dict:
        if not isinstance(value, dict):
            return {}
        return {str(key): val for key, val in value.items() if val in _PROVENANCE_VALUES}

    def to_metadata(self, *, researched_at: str) -> dict[str, Any]:
        return {
            **self.model_dump(),
            "researched_at": researched_at,
        }
