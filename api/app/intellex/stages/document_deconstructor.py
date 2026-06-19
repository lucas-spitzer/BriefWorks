from __future__ import annotations

from typing import Any

from app.intellex.heading_classification import is_chapter_boundary_heading
from app.intellex.stages.deconstructor_models import (
    DocumentChapter,
    DocumentDeconstructorOutput,
    validate_chapter_segmentation,
)
from app.mathesys.chapter_grouping import group_segments_into_chapters


class DocumentDeconstructorStage:
    """Segment prepared NDR text into chapter boundaries deterministically.

    Chapter/part headings start a new top-level chapter; doctrinal subsection
    headings (ALL CAPS titles, etc.) remain inside the chapter as segments.
    """

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
    ) -> tuple[DocumentDeconstructorOutput, dict[str, Any]]:
        del source_metadata  # reserved for future metadata-aware rules

        if not segments:
            raise RuntimeError("NDR segments are required for document deconstruction.")

        all_segment_ids = {str(segment["id"]) for segment in segments}
        chapters = self._chapters_from_segments(segments)
        validate_chapter_segmentation(chapters, all_segment_ids=all_segment_ids)

        return DocumentDeconstructorOutput(chapters=chapters), {
            "model": "deterministic-chapter-boundaries",
            "token_usage": {},
            "baseline_chapter_count": len(chapters),
        }

    def _chapters_from_segments(
        self,
        segments: list[dict[str, Any]],
    ) -> list[DocumentChapter]:
        grouped = group_segments_into_chapters(segments)

        return [
            DocumentChapter(
                sequence_index=index,
                title=str(chapter.get("title") or "Untitled Section"),
                level=1,
                segment_ids=[
                    str(segment["id"])
                    for segment in chapter.get("segments", [])
                ],
            )
            for index, chapter in enumerate(grouped)
        ]
