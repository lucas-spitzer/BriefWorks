from __future__ import annotations

import json
import re
from typing import Any

from app.intellex.skills.deconstructor_models import (
    DocumentChapter,
    DocumentDeconstructorOutput,
    validate_chapter_segmentation,
)
from app.mathesys.chapter_grouping import group_segments_into_chapters
from app.services.openai_client import OpenAIClient

_SECTION_LEVEL_RE = re.compile(
    r"^(section|annex)\b",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You segment prepared documents into chapters and sections for downstream processing.

Each chapter is a JSON object with EXACTLY these keys:
- "sequence_index": integer starting at 0 in reading order
- "title": string — heading for this chapter or section
- "level": integer — 1 for chapter/part/unit, 2 for section/subsection
- "segment_ids": array of segment_id strings in reading order

Rules:
- Every provided segment_id must appear in exactly one chapter.
- Do not drop, rename, or rewrite segment text — only assign boundaries.
- Merge false splits when consecutive chapters are really one section.
- Split when a heading segment is really body text misclassified as a heading.
- Align with doctrine and book conventions: Chapter N, Section 2-1, Part I, etc.
- Return valid JSON with a top-level "chapters" array only."""

USER_TEMPLATE = """Source metadata:
{source_metadata}

Baseline chapter segmentation:
{baseline_json}

Return JSON in exactly this shape:
{{ "chapters": [ {{ "sequence_index": 0, "title": "string", "level": 1, "segment_ids": ["string"] }} ] }}"""


class DocumentDeconstructorSkill:
    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
        chapter_batch_size: int = 8,
    ) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.chapter_batch_size = chapter_batch_size

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
    ) -> tuple[DocumentDeconstructorOutput, dict[str, Any]]:
        if not segments:
            raise RuntimeError("NDR segments are required for document deconstruction.")

        segment_index = {str(segment["id"]): segment for segment in segments}
        all_segment_ids = set(segment_index)
        baseline = self._baseline_chapters(segments)

        batches = [
            baseline[index : index + self.chapter_batch_size]
            for index in range(0, len(baseline), self.chapter_batch_size)
        ]

        refined_chapters: list[DocumentChapter] = []
        token_usage: dict[str, int] = {}
        model = self.openai_client.model

        for batch_index, batch in enumerate(batches):
            batch_output, execution = self._refine_batch(
                source_metadata=source_metadata,
                baseline_chapters=batch,
                segment_index=segment_index,
                batch_index=batch_index,
            )
            model = execution["model"]

            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            refined_chapters.extend(batch_output.chapters)

        normalized = self._normalize_sequence(refined_chapters)
        validate_chapter_segmentation(normalized, all_segment_ids=all_segment_ids)

        return DocumentDeconstructorOutput(chapters=normalized), {
            "model": model,
            "token_usage": token_usage,
            "baseline_chapter_count": len(baseline),
        }

    def _infer_level(self, title: str) -> int:
        if _SECTION_LEVEL_RE.search(title.strip()):
            return 2
        return 1

    def _baseline_chapters(self, segments: list[dict[str, Any]]) -> list[DocumentChapter]:
        grouped = group_segments_into_chapters(segments)

        return [
            DocumentChapter(
                sequence_index=index,
                title=str(chapter.get("title") or "Untitled Section"),
                level=self._infer_level(str(chapter.get("title") or "")),
                segment_ids=[str(segment["id"]) for segment in chapter.get("segments", [])],
            )
            for index, chapter in enumerate(grouped)
        ]

    def _format_baseline_for_llm(
        self,
        *,
        baseline_chapters: list[DocumentChapter],
        segment_index: dict[str, dict[str, Any]],
    ) -> str:
        payload: list[dict[str, Any]] = []

        for chapter in baseline_chapters:
            payload.append(
                {
                    "sequence_index": chapter.sequence_index,
                    "title": chapter.title,
                    "level": chapter.level,
                    "segments": [
                        {
                            "segment_id": segment_id,
                            "kind": segment_index[segment_id].get("kind"),
                            "text": str(segment_index[segment_id].get("text") or "")[:240],
                        }
                        for segment_id in chapter.segment_ids
                        if segment_id in segment_index
                    ],
                },
            )

        return json.dumps(payload, indent=2)

    def _refine_batch(
        self,
        *,
        source_metadata: dict[str, Any],
        baseline_chapters: list[DocumentChapter],
        segment_index: dict[str, dict[str, Any]],
        batch_index: int,
    ) -> tuple[DocumentDeconstructorOutput, dict[str, Any]]:
        batch_segment_ids = {
            segment_id
            for chapter in baseline_chapters
            for segment_id in chapter.segment_ids
        }

        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=json.dumps(
                    {
                        **source_metadata,
                        "deconstruct_batch_index": batch_index,
                    },
                    indent=2,
                ),
                baseline_json=self._format_baseline_for_llm(
                    baseline_chapters=baseline_chapters,
                    segment_index=segment_index,
                ),
            ),
        )

        output = DocumentDeconstructorOutput.model_validate(result.content)
        filtered_chapters: list[DocumentChapter] = []

        for chapter in output.chapters:
            segment_ids = [
                segment_id
                for segment_id in chapter.segment_ids
                if segment_id in batch_segment_ids
            ]
            if not segment_ids:
                continue
            filtered_chapters.append(
                DocumentChapter(
                    sequence_index=chapter.sequence_index,
                    title=chapter.title,
                    level=chapter.level,
                    segment_ids=segment_ids,
                ),
            )

        if not filtered_chapters:
            return DocumentDeconstructorOutput(chapters=baseline_chapters), {
                "model": result.model,
                "token_usage": result.token_usage,
            }

        return DocumentDeconstructorOutput(chapters=filtered_chapters), {
            "model": result.model,
            "token_usage": result.token_usage,
        }

    def _normalize_sequence(self, chapters: list[DocumentChapter]) -> list[DocumentChapter]:
        ordered = sorted(chapters, key=lambda chapter: chapter.sequence_index)

        return [
            DocumentChapter(
                sequence_index=index,
                title=chapter.title,
                level=chapter.level,
                segment_ids=chapter.segment_ids,
            )
            for index, chapter in enumerate(ordered)
        ]
