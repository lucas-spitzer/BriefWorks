from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

DocumentType = Literal[
    "military_doctrine",
    "research_paper",
    "white_paper",
    "report",
    "technical_manual",
    "standard",
    "policy",
    "legal_document",
    "thesis",
    "book",
    "unknown",
]

_DOCUMENT_TYPES = {
    "military_doctrine",
    "research_paper",
    "white_paper",
    "report",
    "technical_manual",
    "standard",
    "policy",
    "legal_document",
    "thesis",
    "book",
    "unknown",
}
_PROVENANCE_VALUES = {"document", "web", "inferred"}

DocumentStatus = Literal[
    "current",
    "superseded",
    "rescinded",
    "withdrawn",
    "draft",
    "unknown",
]

_DOCUMENT_STATUSES = {
    "current",
    "superseded",
    "rescinded",
    "withdrawn",
    "draft",
    "unknown",
}

_RELATED_DOCUMENT_RELATIONS = {
    "supersedes",
    "superseded_by",
    "implements",
    "implemented_by",
    "companion",
    "part_of",
    "references",
    "related",
}


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
    purpose: str | None = None
    target_audience: str | None = None
    scope: str | None = None
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


class WebSource(BaseModel):
    """A web citation backing one or more enrichment fields."""

    url: str
    title: str | None = None
    publisher: str | None = None
    supports: list[str] = Field(default_factory=list)

    @field_validator("supports", mode="before")
    @classmethod
    def _coerce_supports(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        return []


class RelatedDocument(BaseModel):
    title: str
    identifier: str | None = None
    url: str | None = None
    relation: str = "related"

    @field_validator("relation", mode="before")
    @classmethod
    def _coerce_relation(cls, value: Any) -> str:
        if isinstance(value, str) and value in _RELATED_DOCUMENT_RELATIONS:
            return value
        return "related"


class WebEnrichmentOutput(BaseModel):
    """Web-verified profile facts layered on top of document-extracted research.

    Every populated field must be backed by an entry in ``web_sources``; the
    merge layer treats document-extracted values as authoritative on conflict.
    """

    status: DocumentStatus = "unknown"
    superseded_by: str | None = None
    canonical_url: str | None = None
    publication_date_public: str | None = None
    publisher_context: str | None = None
    public_abstract: str | None = None
    confirmations: list[str] = Field(default_factory=list)
    corrections: dict[str, str] = Field(default_factory=dict)
    related_documents: list[RelatedDocument] = Field(default_factory=list)
    web_sources: list[WebSource] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    # Set by the stage, not the model: whether a web search actually ran.
    searched: bool = True
    skip_reason: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value: Any) -> str:
        if isinstance(value, str) and value in _DOCUMENT_STATUSES:
            return value
        return "unknown"

    @field_validator("confirmations", mode="before")
    @classmethod
    def _coerce_confirmations(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        return []

    @field_validator("corrections", mode="before")
    @classmethod
    def _coerce_corrections(cls, value: Any) -> dict:
        if not isinstance(value, dict):
            return {}
        return {
            str(key): str(val)
            for key, val in value.items()
            if val not in (None, "")
        }

    @field_validator("related_documents", mode="before")
    @classmethod
    def _coerce_related_documents(cls, value: Any) -> list:
        if not isinstance(value, list):
            return []
        return [
            item
            for item in value
            if isinstance(item, RelatedDocument)
            or (isinstance(item, dict) and str(item.get("title") or "").strip())
        ]

    @field_validator("web_sources", mode="before")
    @classmethod
    def _coerce_web_sources(cls, value: Any) -> list:
        if not isinstance(value, list):
            return []
        return [
            item
            for item in value
            if isinstance(item, WebSource)
            or (isinstance(item, dict) and str(item.get("url") or "").strip())
        ]

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

    def to_metadata(self, *, enriched_at: str) -> dict[str, Any]:
        return {
            **self.model_dump(),
            "enriched_at": enriched_at,
        }
