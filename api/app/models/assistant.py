from typing import Any, Literal

from pydantic import BaseModel, Field

AssistantMode = Literal["discussion", "scenario"]
DiscussionSubmode = Literal["socratic", "euclidean"]


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AssistantChatRequest(BaseModel):
    mode: AssistantMode
    submode: DiscussionSubmode | None = None
    messages: list[AssistantMessage] = Field(default_factory=list)
    # Optional narrowing: restrict retrieval to specific source documents.
    source_ids: list[str] | None = None
    # Required when mode == "scenario" to load its evaluation_criteria/rubric.
    scenario_id: str | None = None


class Citation(BaseModel):
    kind: Literal["segment", "wiki"]
    label: str
    snippet: str
    similarity: float
    reader_link: str | None = None
    locator: dict[str, Any] = Field(default_factory=dict)


class ScenarioEvaluation(BaseModel):
    passed: bool
    score: float | None = None
    feedback: str
    met_criteria: list[str] = Field(default_factory=list)
    missed_criteria: list[str] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[Citation] = Field(default_factory=list)
    evaluation: ScenarioEvaluation | None = None
