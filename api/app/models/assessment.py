from datetime import datetime
from typing import Any

from pydantic import BaseModel


class FlashcardResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None
    production_run_id: str | None
    stage_run_id: str | None
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
    stage_run_id: str | None
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
    stage_run_id: str | None
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
