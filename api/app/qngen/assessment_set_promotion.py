from __future__ import annotations

from typing import Any

from app.qngen.assessment_promotion import build_citations


def _research_title(source_metadata: dict[str, Any]) -> str | None:
    research = source_metadata.get("research")
    if not isinstance(research, dict):
        return None

    title = research.get("title")
    return str(title) if isinstance(title, str) and title.strip() else None


def build_assessment_set_title(
    *,
    source_metadata: dict[str, Any],
    item_count: int,
) -> str:
    title = _research_title(source_metadata)
    if title:
        return f"Assessment Set: {title}"
    return f"Assessment Set ({item_count} items)"


def build_learning_goal(*, assessment_types: list[str]) -> str:
    goals: list[str] = []
    if "flashcards" in assessment_types:
        goals.append("recall")
    if "quizzes" in assessment_types:
        goals.append("understanding")
    if "scenarios" in assessment_types:
        goals.append("application")

    if not goals:
        return "Assess learning from source material."

    return f"Assess {', '.join(goals)} of canonical source concepts."


def promote_assessment_set(
    *,
    workspace_id: str,
    source_id: str,
    production_run_id: str,
    stage_run_id: str,
    stage_id: str,
    stage_version: str,
    source_metadata: dict[str, Any],
    assessment_types: list[str],
    items: list[dict[str, Any]],
    assessment_set_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    set_row = {
        "id": assessment_set_id,
        "workspace_id": workspace_id,
        "source_id": source_id,
        "production_run_id": production_run_id,
        "stage_run_id": stage_run_id,
        "title": build_assessment_set_title(
            source_metadata=source_metadata,
            item_count=len(items),
        ),
        "learning_goal": build_learning_goal(assessment_types=assessment_types),
        "assessment_types": assessment_types,
        "items": items,
        "origin": {
            "stage_run_id": stage_run_id,
            "stage_id": stage_id,
            "stage_version": stage_version,
        },
    }

    flashcard_rows: list[dict[str, Any]] = []
    quiz_rows: list[dict[str, Any]] = []
    scenario_rows: list[dict[str, Any]] = []

    for item in items:
        citations = build_citations(
            wiki_ids=item.get("wiki_ids_cited") or [],
            segment_ids=item.get("source_chunk_ids") or [],
            source_id=source_id,
        )
        common = {
            "workspace_id": workspace_id,
            "source_id": source_id,
            "production_run_id": production_run_id,
            "stage_run_id": stage_run_id,
            "assessment_set_id": assessment_set_id,
            "item_id": item.get("item_id"),
            "citations": citations,
            "origin": {
                "stage_run_id": stage_run_id,
                "stage_id": stage_id,
                "stage_version": stage_version,
            },
        }

        item_type = item.get("type")
        if item_type == "flashcard":
            flashcard_rows.append(
                {
                    **common,
                    "front": item["front"],
                    "back": item["back"],
                    "difficulty": item.get("difficulty") or "medium",
                    "tags": item.get("tags") or [],
                    "subtype": item.get("subtype") or "basic",
                },
            )
        elif item_type == "quiz":
            quiz_rows.append(
                {
                    **common,
                    "question": item["question"],
                    "question_type": item.get("subtype") or "multiple_choice",
                    "options": item.get("choices") or [],
                    "correct_answer": item["correct_answer"],
                    "explanation": item.get("explanation"),
                    "difficulty": item.get("difficulty") or "medium",
                    "subtype": item.get("subtype") or "multiple_choice",
                },
            )
        elif item_type == "scenario":
            scenario_rows.append(
                {
                    **common,
                    "title": item.get("task") or "Scenario",
                    "prompt": item["task"],
                    "context": item.get("situation"),
                    "evaluation_criteria": item.get("expected_response_elements") or [],
                    "difficulty": item.get("difficulty") or "medium",
                    "subtype": item.get("subtype") or "decision_prompt",
                    "rubric": item.get("rubric"),
                },
            )

    return set_row, flashcard_rows, quiz_rows, scenario_rows
