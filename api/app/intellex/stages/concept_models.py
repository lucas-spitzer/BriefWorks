from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Importance = Literal["essential", "supporting", "contextual"]
EntryKind = Literal["term", "concept", "insight"]

_IMPORTANCE_VALUES = {"essential", "supporting", "contextual"}
_ENTRY_KIND_VALUES = {"term", "concept", "insight"}

_CONCEPT_KEY_ALIASES = {
    "term": "term_label",
    "label": "term_label",
    "name": "term_label",
    "description": "definition",
    "meaning": "definition",
    "synonyms": "aliases",
    "prerequisites": "prerequisite_labels",
    "prereqs": "prerequisite_labels",
    "segment_ids": "evidence_segment_ids",
    "segment_id_evidence": "evidence_segment_ids",
    "evidence": "evidence_segment_ids",
    "priority": "importance",
    "kind": "entry_kind",
}


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return []


class DeconstructedConcept(BaseModel):
    term_label: str
    definition: str
    entry_kind: EntryKind = "concept"
    aliases: list[str] = Field(default_factory=list)
    prerequisite_labels: list[str] = Field(default_factory=list)
    pronunciation: str | None = None
    importance: Importance = "supporting"
    evidence_segment_ids: list[str] = Field(default_factory=list)
    evidence_quotes: list[dict[str, str]] = Field(default_factory=list)
    objective_labels: list[str] = Field(default_factory=list)
    confidence: float = 0.5
    chapter_id: str | None = None
    chapter_sequence_index: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized: dict[str, Any] = {}
        for key, value in data.items():
            canonical = _CONCEPT_KEY_ALIASES.get(key, key)
            normalized.setdefault(canonical, value)
        return normalized

    @field_validator("term_label", "definition", mode="before")
    @classmethod
    def _coerce_required_text(cls, value: Any) -> str:
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return str(value)

    @field_validator("aliases", "prerequisite_labels", "evidence_segment_ids", "objective_labels", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)

    @field_validator("evidence_quotes", mode="before")
    @classmethod
    def _coerce_evidence_quotes(cls, value: Any) -> list[dict[str, str]]:
        if not value:
            return []
        if not isinstance(value, list):
            return []
        quotes: list[dict[str, str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            segment_id = item.get("segment_id")
            quote = item.get("quote")
            if segment_id and quote:
                quotes.append({"segment_id": str(segment_id), "quote": str(quote)})
        return quotes

    @field_validator("entry_kind", mode="before")
    @classmethod
    def _coerce_entry_kind(cls, value: Any) -> str:
        if isinstance(value, str) and value in _ENTRY_KIND_VALUES:
            return value
        return "concept"

    @field_validator("importance", mode="before")
    @classmethod
    def _coerce_importance(cls, value: Any) -> str:
        if isinstance(value, str) and value in _IMPORTANCE_VALUES:
            return value
        return "supporting"

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.5
        return min(1.0, max(0.0, number))


class LearningObjective(BaseModel):
    objective_id: str
    statement: str
    bloom_level: str = "understand"
    concept_labels: list[str] = Field(default_factory=list)

    @field_validator("concept_labels", mode="before")
    @classmethod
    def _coerce_concept_labels(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class ChapterKnowledgeOutput(BaseModel):
    chapter_id: str
    chapter_title: str
    sequence_index: int
    segment_ids: list[str] = Field(default_factory=list)
    learning_objectives: list[LearningObjective] = Field(default_factory=list)
    items: list[DeconstructedConcept] = Field(default_factory=list)

    @field_validator("segment_ids", mode="before")
    @classmethod
    def _coerce_segment_ids(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class ExtractChapterKnowledgeOutput(BaseModel):
    chapters: list[ChapterKnowledgeOutput] = Field(default_factory=list)
    items: list[DeconstructedConcept] = Field(default_factory=list)
    learning_objectives: list[LearningObjective] = Field(default_factory=list)

    @field_validator("chapters", mode="before")
    @classmethod
    def _coerce_chapters(cls, value: Any) -> list[ChapterKnowledgeOutput]:
        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, (dict, ChapterKnowledgeOutput))
            ]
        return []

    @field_validator("items", mode="before")
    @classmethod
    def _coerce_items(cls, value: Any) -> list[DeconstructedConcept]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, (dict, DeconstructedConcept))]
        return []
