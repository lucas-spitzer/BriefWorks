from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class DocumentChapter(BaseModel):
    sequence_index: int
    title: str
    level: int = 1
    segment_ids: list[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def _coerce_title(cls, value: Any) -> str:
        if isinstance(value, str):
            return value.strip() or "Untitled Section"
        if value is None:
            return "Untitled Section"
        return str(value).strip() or "Untitled Section"

    @field_validator("level", "sequence_index", mode="before")
    @classmethod
    def _coerce_int(cls, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @field_validator("segment_ids", mode="before")
    @classmethod
    def _coerce_segment_ids(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        return []


class DocumentDeconstructorOutput(BaseModel):
    chapters: list[DocumentChapter] = Field(default_factory=list)

    @field_validator("chapters", mode="before")
    @classmethod
    def _coerce_chapters(cls, value: Any) -> list[DocumentChapter]:
        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, (dict, DocumentChapter))
            ]
        return []


def validate_chapter_segmentation(
    chapters: list[DocumentChapter],
    *,
    all_segment_ids: set[str],
) -> None:
    if not chapters:
        raise RuntimeError("Deconstruct produced no chapters.")

    assigned: list[str] = []
    for chapter in chapters:
        if not chapter.segment_ids:
            raise RuntimeError(f"Chapter {chapter.sequence_index!r} has no segments.")
        assigned.extend(chapter.segment_ids)

    assigned_set = set(assigned)
    if len(assigned) != len(assigned_set):
        raise RuntimeError("Deconstruct assigned one or more segments to multiple chapters.")

    if assigned_set != all_segment_ids:
        missing = sorted(all_segment_ids - assigned_set)
        extra = sorted(assigned_set - all_segment_ids)
        details: list[str] = []
        if missing:
            details.append(f"missing={missing[:5]}")
        if extra:
            details.append(f"extra={extra[:5]}")
        raise RuntimeError(
            "Deconstruct chapter segmentation does not cover all segments "
            f"({', '.join(details)}).",
        )
