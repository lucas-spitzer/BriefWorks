from __future__ import annotations

import json
from typing import Any

from app.intellex.chapter_formatting import format_chapter_segments_for_llm
from app.intellex.skills.concept_models import (
    ChapterKnowledgeOutput,
    DeconstructedConcept,
    ExtractChapterKnowledgeOutput,
)
from app.intellex.wiki_slug import normalize_slug
from app.mathesys.chapter_grouping import hydrate_chapters_from_rows
from app.services.openai_client import OpenAIClient

_IMPORTANCE_ORDER = {"essential": 3, "supporting": 2, "contextual": 1}

SYSTEM_PROMPT = """You extract learning knowledge from a single document chapter.

Your job is EXTRACTION, not summarization. Identify what a reader must understand from this chapter only.

Each item is a JSON object with EXACTLY these keys:
- "entry_kind": one of "term", "concept", or "insight"
- "term_label": string — canonical name or insight headline
- "definition": string — definition (term/concept) or explanatory insight text grounded in the chapter
- "aliases": array of strings (use [] if none)
- "prerequisite_labels": array of strings (use [] if none)
- "pronunciation": string or null — phonetic hint for acronyms/uncommon terms
- "importance": one of "essential", "supporting", or "contextual"
- "evidence_segment_ids": array of segment_id strings from the provided chapter segments
- "confidence": number from 0.0 to 1.0

entry_kind rules:
- "term": vocabulary, acronyms, named entities the reader must know
- "concept": ideas, principles, frameworks defined or central to the chapter
- "insight": non-vocabulary takeaways — causal relationships, doctrinal implications, lessons grounded in chapter text

Rules:
- Ground every item in the provided chapter segments only.
- Cite evidence_segment_ids from the chapter segment list.
- Do not duplicate the same item under different labels; use aliases instead.
- Do not summarize the whole chapter.
- Return valid JSON with a top-level "items" array only."""

USER_TEMPLATE = """Source metadata:
{source_metadata}

Chapter:
- chapter_id: {chapter_id}
- title: {chapter_title}
- sequence_index: {sequence_index}
- level: {chapter_level}

Chapter segments:
{segments_json}

Existing workspace labels (deduplicate using aliases when these match):
{existing_labels}

Return JSON in exactly this shape:
{{ "items": [ {{ "entry_kind": "concept", "term_label": "string", "definition": "string", "aliases": [], "prerequisite_labels": [], "pronunciation": null, "importance": "essential", "evidence_segment_ids": ["string"], "confidence": 0.0 }} ] }}"""


class ExtractChapterKnowledgeSkill:
    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
    ) -> None:
        self.openai_client = openai_client or OpenAIClient()

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        chapter_rows: list[dict[str, Any]],
        segments: list[dict[str, Any]],
        existing_labels: list[str] | None = None,
    ) -> tuple[ExtractChapterKnowledgeOutput, dict[str, Any]]:
        if not chapter_rows:
            raise RuntimeError("Document chapters are required for knowledge extraction.")

        segment_index = {str(segment["id"]): segment for segment in segments}
        chapter_outputs: list[ChapterKnowledgeOutput] = []
        token_usage: dict[str, int] = {}
        model = self.openai_client.model

        for chapter_row in sorted(chapter_rows, key=lambda row: row.get("sequence_index", 0)):
            chapter_id = str(chapter_row["id"])
            hydrated = hydrate_chapters_from_rows([chapter_row], segment_index)

            if not hydrated:
                raise RuntimeError(f"Chapter {chapter_id} has no resolvable segments.")

            chapter_segments = hydrated[0]["segments"]
            chapter_title = str(chapter_row.get("title") or hydrated[0].get("title") or "Untitled")
            sequence_index = int(chapter_row.get("sequence_index") or 0)
            chapter_level = int(chapter_row.get("level") or 1)

            items, execution = self._extract_chapter(
                source_metadata=source_metadata,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                sequence_index=sequence_index,
                chapter_level=chapter_level,
                segments=chapter_segments,
                existing_labels=existing_labels or [],
            )
            model = execution["model"]

            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            chapter_outputs.append(
                ChapterKnowledgeOutput(
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    sequence_index=sequence_index,
                    items=items,
                ),
            )

        merged_items = merge_knowledge_items(
            [item for chapter in chapter_outputs for item in chapter.items],
        )

        return ExtractChapterKnowledgeOutput(
            chapters=chapter_outputs,
            items=merged_items,
        ), {
            "model": model,
            "token_usage": token_usage,
            "chapter_count": len(chapter_outputs),
        }

    def _extract_chapter(
        self,
        *,
        source_metadata: dict[str, Any],
        chapter_id: str,
        chapter_title: str,
        sequence_index: int,
        chapter_level: int,
        segments: list[dict[str, Any]],
        existing_labels: list[str],
    ) -> tuple[list[DeconstructedConcept], dict[str, Any]]:
        segments_json, _ = format_chapter_segments_for_llm(segments)
        chapter_segment_ids = {str(segment["id"]) for segment in segments}

        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=json.dumps(source_metadata, indent=2),
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                sequence_index=sequence_index,
                chapter_level=chapter_level,
                segments_json=segments_json,
                existing_labels=json.dumps(existing_labels),
            ),
        )

        raw_items = result.content.get("items") or []
        items: list[DeconstructedConcept] = []

        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            concept = DeconstructedConcept.model_validate(raw)
            concept.chapter_id = chapter_id
            concept.chapter_sequence_index = sequence_index
            concept.evidence_segment_ids = [
                segment_id
                for segment_id in concept.evidence_segment_ids
                if segment_id in chapter_segment_ids
            ]
            if concept.term_label and concept.definition:
                items.append(concept)

        return items, {
            "model": result.model,
            "token_usage": result.token_usage,
        }


def merge_knowledge_items(items: list[DeconstructedConcept]) -> list[DeconstructedConcept]:
    merged: dict[tuple[str, str], DeconstructedConcept] = {}

    for item in items:
        key = (normalize_slug(item.term_label), item.entry_kind)
        existing = merged.get(key)

        if not existing:
            merged[key] = item.model_copy(deep=True)
            continue

        existing.aliases = sorted(
            {
                *existing.aliases,
                *item.aliases,
                item.term_label,
            },
        )
        existing.evidence_segment_ids = sorted(
            {
                *existing.evidence_segment_ids,
                *item.evidence_segment_ids,
            },
        )
        if _IMPORTANCE_ORDER.get(item.importance, 0) > _IMPORTANCE_ORDER.get(existing.importance, 0):
            existing.importance = item.importance
        if item.confidence > existing.confidence:
            existing.confidence = item.confidence

    return list(merged.values())
