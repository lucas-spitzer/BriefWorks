from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

FlashcardSubtype = Literal["basic", "term_definition", "cloze"]
QuizSubtype = Literal[
    "multiple_choice",
    "true_false_correction",
    "multiple_select",
]
ScenarioSubtype = Literal["decision_prompt", "rubric_response"]
Difficulty = Literal["easy", "medium", "hard"]

_DIFFICULTY_VALUES = {"easy", "medium", "hard"}
_FLASHCARD_SUBTYPES = {"basic", "term_definition", "cloze"}
_QUIZ_SUBTYPES = {"multiple_choice", "true_false_correction", "multiple_select"}
_SCENARIO_SUBTYPES = {"decision_prompt", "rubric_response"}


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return []


class AssessmentItemBase(BaseModel):
    item_id: str
    type: str
    subtype: str
    difficulty: Difficulty = "medium"
    wiki_ids_cited: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("item_id", mode="before")
    @classmethod
    def _ensure_item_id(cls, value: Any) -> str:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return str(uuid.uuid4())

    @field_validator("difficulty", mode="before")
    @classmethod
    def _coerce_difficulty(cls, value: Any) -> str:
        if isinstance(value, str) and value in _DIFFICULTY_VALUES:
            return value
        return "medium"

    @field_validator("wiki_ids_cited", "source_chunk_ids", "tags", mode="before")
    @classmethod
    def _coerce_lists(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class FlashcardItem(AssessmentItemBase):
    type: Literal["flashcard"] = "flashcard"
    subtype: FlashcardSubtype = "term_definition"
    front: str
    back: str

    @field_validator("subtype", mode="before")
    @classmethod
    def _coerce_subtype(cls, value: Any) -> str:
        if isinstance(value, str) and value in _FLASHCARD_SUBTYPES:
            return value
        return "term_definition"

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("type") != "flashcard":
            data = {**data, "type": "flashcard"}
        if "segment_ids_used" in data and "source_chunk_ids" not in data:
            data["source_chunk_ids"] = data["segment_ids_used"]
        return data


class QuizItem(AssessmentItemBase):
    type: Literal["quiz"] = "quiz"
    subtype: QuizSubtype = "multiple_choice"
    question: str
    choices: list[str] = Field(default_factory=list)
    correct_answer: str
    explanation: str | None = None

    @field_validator("subtype", mode="before")
    @classmethod
    def _coerce_subtype(cls, value: Any) -> str:
        if isinstance(value, str):
            if value in _QUIZ_SUBTYPES:
                return value
            if value == "true_false":
                return "true_false_correction"
        return "multiple_choice"

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("type") != "quiz":
            data = {**data, "type": "quiz"}
        if "options" in data and "choices" not in data:
            data["choices"] = data["options"]
        if "segment_ids_used" in data and "source_chunk_ids" not in data:
            data["source_chunk_ids"] = data["segment_ids_used"]
        return data

    @field_validator("choices", mode="before")
    @classmethod
    def _coerce_choices(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class ScenarioItem(AssessmentItemBase):
    type: Literal["scenario"] = "scenario"
    subtype: ScenarioSubtype = "decision_prompt"
    situation: str | None = None
    task: str
    expected_response_elements: list[str] = Field(default_factory=list)
    rubric: dict[str, str] | None = None

    @field_validator("subtype", mode="before")
    @classmethod
    def _coerce_subtype(cls, value: Any) -> str:
        if isinstance(value, str) and value in _SCENARIO_SUBTYPES:
            return value
        return "decision_prompt"

    @model_validator(mode="before")
    @classmethod
    def _normalize_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("type") != "scenario":
            data = {**data, "type": "scenario"}
        if "prompt" in data and "task" not in data:
            data["task"] = data["prompt"]
        if "context" in data and "situation" not in data:
            data["situation"] = data["context"]
        if "evaluation_criteria" in data and "expected_response_elements" not in data:
            data["expected_response_elements"] = data["evaluation_criteria"]
        if "segment_ids_used" in data and "source_chunk_ids" not in data:
            data["source_chunk_ids"] = data["segment_ids_used"]
        return data

    @field_validator("expected_response_elements", mode="before")
    @classmethod
    def _coerce_elements(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)


class AssessmentBatchOutput(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_items(self) -> AssessmentBatchOutput:
        parsed_items: list[dict[str, Any]] = []

        for raw_item in self.items:
            item_type = raw_item.get("type")
            if item_type == "flashcard":
                parsed_items.append(FlashcardItem.model_validate(raw_item).model_dump())
            elif item_type == "quiz":
                parsed_items.append(QuizItem.model_validate(raw_item).model_dump())
            elif item_type == "scenario":
                parsed_items.append(ScenarioItem.model_validate(raw_item).model_dump())

        self.items = parsed_items
        return self


class AssessmentSetGenOutput(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)

    def add_batch(self, batch: AssessmentBatchOutput) -> None:
        self.items.extend(batch.items)
