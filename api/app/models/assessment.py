from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FlashcardResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None
    production_run_id: str | None
    skill_run_id: str | None
    assessment_set_id: str | None = None
    item_id: str | None = None
    subtype: str | None = None
    front: str
    back: str
    difficulty: str
    tags: list[str]
    citations: list[dict[str, Any]]
    origin: dict[str, Any]
    created_at: datetime


class QuizResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None
    production_run_id: str | None
    skill_run_id: str | None
    assessment_set_id: str | None = None
    item_id: str | None = None
    subtype: str | None = None
    question: str
    question_type: str
    options: list[Any]
    correct_answer: str
    explanation: str | None
    difficulty: str
    citations: list[dict[str, Any]]
    origin: dict[str, Any]
    created_at: datetime


class ScenarioResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None
    production_run_id: str | None
    skill_run_id: str | None
    assessment_set_id: str | None = None
    item_id: str | None = None
    subtype: str | None = None
    title: str
    prompt: str
    context: str | None
    evaluation_criteria: list[Any]
    rubric: dict[str, Any] | None = None
    difficulty: str
    citations: list[dict[str, Any]]
    origin: dict[str, Any]
    created_at: datetime


class AssessmentSetSummaryResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None
    production_run_id: str | None
    skill_run_id: str | None
    title: str
    learning_goal: str | None
    assessment_types: list[str]
    item_count: int
    created_at: datetime


class AssessmentSetResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None
    production_run_id: str | None
    skill_run_id: str | None
    title: str
    learning_goal: str | None
    assessment_types: list[str]
    items: list[dict[str, Any]]
    origin: dict[str, Any]
    created_at: datetime
