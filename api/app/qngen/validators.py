from __future__ import annotations

import re
from typing import Any

from app.qngen.canonical_context import ConceptCard

_MAX_FLASHCARDS_PER_CONCEPT = 2
_MAX_QUIZZES_PER_CONCEPT = 1
_MAX_SCENARIOS_PER_CONCEPT = 1


def validate_assessment_items(
    *,
    items: list[dict[str, Any]],
    concepts: list[ConceptCard],
    segment_ids: set[str],
    wiki_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labels_by_wiki_id = {
        concept.wiki_id: {
            concept.preferred_label.lower(),
            *[alias.lower() for alias in concept.aliases],
        }
        for concept in concepts
    }
    all_labels = {
        label
        for labels in labels_by_wiki_id.values()
        for label in labels
    }

    validated: list[dict[str, Any]] = []
    dropped_invalid_citations = 0
    dropped_invalid_quiz_answer = 0
    dropped_per_concept_cap = 0
    label_warnings: list[str] = []

    flashcard_counts: dict[str, int] = {}
    quiz_counts: dict[str, int] = {}
    scenario_counts: dict[str, int] = {}

    for item in items:
        cited_wiki = set(item.get("wiki_ids_cited") or [])
        cited_segments = set(item.get("source_chunk_ids") or [])

        if cited_wiki - wiki_ids or cited_segments - segment_ids:
            dropped_invalid_citations += 1
            continue

        item_type = item.get("type")
        primary_wiki = next(iter(cited_wiki), None)

        if item_type == "quiz":
            choices = item.get("choices") or []
            correct_answer = item.get("correct_answer")
            subtype = item.get("subtype", "multiple_choice")

            if subtype == "multiple_select":
                if isinstance(correct_answer, str):
                    answers = [part.strip() for part in correct_answer.split(";") if part.strip()]
                    if answers and not all(answer in choices for answer in answers):
                        dropped_invalid_quiz_answer += 1
                        continue
            elif correct_answer not in choices and subtype in {
                "multiple_choice",
                "true_false_correction",
            }:
                dropped_invalid_quiz_answer += 1
                continue

        if primary_wiki:
            if item_type == "flashcard":
                count = flashcard_counts.get(primary_wiki, 0)
                if count >= _MAX_FLASHCARDS_PER_CONCEPT:
                    dropped_per_concept_cap += 1
                    continue
                flashcard_counts[primary_wiki] = count + 1
            elif item_type == "quiz":
                count = quiz_counts.get(primary_wiki, 0)
                if count >= _MAX_QUIZZES_PER_CONCEPT:
                    dropped_per_concept_cap += 1
                    continue
                quiz_counts[primary_wiki] = count + 1
            elif item_type == "scenario":
                count = scenario_counts.get(primary_wiki, 0)
                if count >= _MAX_SCENARIOS_PER_CONCEPT:
                    dropped_per_concept_cap += 1
                    continue
                scenario_counts[primary_wiki] = count + 1

        text_blob = _item_text(item).lower()
        if text_blob and all_labels and not contains_canonical_label(text_blob, all_labels):
            label_warnings.append(
                f"Item {item.get('item_id')} may not reference a canonical label.",
            )

        validated.append(item)

    report = {
        "input_count": len(items),
        "validated_count": len(validated),
        "dropped_invalid_citations": dropped_invalid_citations,
        "dropped_invalid_quiz_answer": dropped_invalid_quiz_answer,
        "dropped_per_concept_cap": dropped_per_concept_cap,
        "label_warnings": label_warnings,
    }
    return validated, report


def _item_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("front"),
        item.get("back"),
        item.get("question"),
        item.get("situation"),
        item.get("task"),
    ]
    return " ".join(part for part in parts if isinstance(part, str))


def contains_canonical_label(text: str, labels: set[str]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(label)}\b", lowered) for label in labels)
