from __future__ import annotations

import json
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.intellex.ndr_formatting import format_segments_for_llm

Importance = Literal["essential", "supporting", "contextual"]

_IMPORTANCE_ORDER = {"essential": 0, "supporting": 1, "contextual": 2}


class ConceptCard(BaseModel):
    wiki_id: str
    preferred_label: str
    definition: str
    aliases: list[str] = Field(default_factory=list)
    pronunciation: str | None = None
    importance: Importance = "supporting"
    prerequisite_labels: list[str] = Field(default_factory=list)
    evidence_segment_ids: list[str] = Field(default_factory=list)
    evidence_segments: list[dict[str, Any]] = Field(default_factory=list)


def _evidence_for_source(
    evidence: list[dict[str, Any]] | None,
    source_id: str,
) -> list[dict[str, Any]]:
    if not evidence:
        return []

    return [
        record
        for record in evidence
        if record.get("source_id") == source_id and record.get("segment_id")
    ]


def build_source_concepts(
    *,
    wiki_entries: list[dict[str, Any]],
    source_id: str,
    segments: list[dict[str, Any]],
) -> list[ConceptCard]:
    segment_index = {str(segment["id"]): segment for segment in segments}
    wiki_by_id = {str(entry["id"]): entry for entry in wiki_entries}
    concepts: list[ConceptCard] = []

    for entry in wiki_entries:
        if entry.get("status") != "canonical":
            continue

        source_evidence = _evidence_for_source(entry.get("evidence"), source_id)
        if not source_evidence:
            continue

        segment_ids = [str(record["segment_id"]) for record in source_evidence]
        resolved_segments: list[dict[str, Any]] = []

        for segment_id in segment_ids:
            segment = segment_index.get(segment_id)
            if not segment:
                continue

            resolved_segments.append(
                {
                    "segment_id": segment_id,
                    "kind": segment.get("kind"),
                    "text": segment.get("text"),
                    "page": (segment.get("locator") or {}).get("page"),
                },
            )

        if not resolved_segments:
            continue

        prerequisite_ids = entry.get("prerequisites") or []
        prerequisite_labels = [
            str(wiki_by_id[prereq_id]["preferred_label"])
            for prereq_id in prerequisite_ids
            if prereq_id in wiki_by_id
        ]

        concepts.append(
            ConceptCard(
                wiki_id=str(entry["id"]),
                preferred_label=str(entry.get("preferred_label") or ""),
                definition=str(entry.get("definition") or ""),
                aliases=[str(alias) for alias in (entry.get("aliases") or [])],
                pronunciation=entry.get("pronunciation"),
                importance=entry.get("importance") or "supporting",
                prerequisite_labels=prerequisite_labels,
                evidence_segment_ids=segment_ids,
                evidence_segments=resolved_segments,
            ),
        )

    concepts.sort(
        key=lambda concept: (
            _IMPORTANCE_ORDER.get(concept.importance, 99),
            concept.preferred_label.lower(),
        ),
    )
    return concepts


def batch_concepts(
    concepts: list[ConceptCard],
    *,
    batch_size: int | None = None,
) -> list[list[ConceptCard]]:
    if not concepts:
        return []

    resolved_batch_size = batch_size or int(os.getenv("QNGEN_CONCEPT_BATCH_SIZE", "8"))
    batches: list[list[ConceptCard]] = []

    for start in range(0, len(concepts), resolved_batch_size):
        batches.append(concepts[start : start + resolved_batch_size])

    return batches


def format_concepts_for_llm(concepts: list[ConceptCard]) -> str:
    payload = [
        {
            "wiki_id": concept.wiki_id,
            "preferred_label": concept.preferred_label,
            "definition": concept.definition,
            "aliases": concept.aliases,
            "pronunciation": concept.pronunciation,
            "importance": concept.importance,
            "prerequisite_labels": concept.prerequisite_labels,
            "evidence_segments": concept.evidence_segments,
        }
        for concept in concepts
    ]
    return json.dumps(payload, indent=2)


def format_concept_segments_for_llm(concepts: list[ConceptCard]) -> str:
    segments: list[dict[str, Any]] = []
    seen_segment_ids: set[str] = set()

    for concept in concepts:
        for segment in concept.evidence_segments:
            segment_id = str(segment.get("segment_id"))
            if segment_id in seen_segment_ids:
                continue
            seen_segment_ids.add(segment_id)
            segments.append(segment)

    return format_segments_for_llm(
        [
            {
                "id": segment["segment_id"],
                "kind": segment.get("kind"),
                "text": segment.get("text"),
                "locator": {"page": segment.get("page")},
            }
            for segment in segments
        ],
    )
