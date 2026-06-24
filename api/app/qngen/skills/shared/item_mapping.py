from __future__ import annotations

import uuid
from typing import Any, Literal

ArtifactType = Literal["flashcard", "quiz", "scenario"]


def normalize_question_type(subtype: str | None) -> str:
    mapping = {
        "multiple_choice": "multiple_choice",
        "true_false": "true_false",
        "true_false_correction": "true_false",
        "short_answer": "short_answer",
        "multiple_select": "multiple_choice",
    }
    return mapping.get(subtype or "multiple_choice", "multiple_choice")


def assessment_item_to_flashcard(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "front": item.get("front") or "",
        "back": item.get("back") or "",
        "difficulty": item.get("difficulty") or "medium",
        "tags": item.get("tags") or [],
        "wiki_ids_cited": item.get("wiki_ids_cited") or [],
        "segment_ids_used": item.get("source_chunk_ids") or [],
    }


def assessment_item_to_quiz(item: dict[str, Any]) -> dict[str, Any]:
    subtype = item.get("subtype") or "multiple_choice"
    correct_answer = item.get("correct_answer") or ""
    choices = item.get("choices") or []

    if subtype == "multiple_select" and isinstance(correct_answer, list):
        correct_answer = "; ".join(correct_answer)

    return {
        "question": item.get("question") or "",
        "question_type": normalize_question_type(subtype),
        "options": choices,
        "correct_answer": correct_answer,
        "explanation": item.get("explanation"),
        "difficulty": item.get("difficulty") or "medium",
        "wiki_ids_cited": item.get("wiki_ids_cited") or [],
        "segment_ids_used": item.get("source_chunk_ids") or [],
    }


def assessment_item_to_scenario(item: dict[str, Any]) -> dict[str, Any]:
    task = item.get("task") or item.get("prompt") or ""
    situation = item.get("situation") or item.get("context")
    rubric = item.get("rubric") or {}
    criteria = item.get("expected_response_elements") or []

    if isinstance(rubric, dict) and not criteria:
        criteria = [str(value) for value in rubric.values() if value]

    return {
        "title": item.get("title") or task[:80] or "Scenario",
        "prompt": task,
        "context": situation,
        "evaluation_criteria": criteria,
        "difficulty": item.get("difficulty") or "medium",
        "wiki_ids_cited": item.get("wiki_ids_cited") or [],
        "segment_ids_used": item.get("source_chunk_ids") or [],
    }


def ensure_item_ids(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for item in items:
        row = dict(item)
        if not row.get("item_id"):
            row["item_id"] = str(uuid.uuid4())
        normalized.append(row)

    return normalized
