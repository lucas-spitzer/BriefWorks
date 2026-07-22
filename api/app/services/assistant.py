from __future__ import annotations

import asyncio
import json
from typing import Any

from app.models.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    Citation,
    ScenarioEvaluation,
)
from app.repositories.assessments import AssessmentRepository
from app.services.openai_client import OpenAIClient
from app.services.retrieval import RetrievedChunk, RetrievalService

# --- System prompts -------------------------------------------------------
# Same retrieval core; the mode/submode only swaps the instructions.

_GROUNDING_RULES = (
    "You are a study assistant for a reading app. Answer ONLY from the SOURCE "
    "MATERIAL below. If the material does not cover the question, say so plainly "
    "and do not invent facts. When you use a passage, cite it inline as [n] using "
    "the numbers shown in the source material."
)

SYSTEM_PROMPTS: dict[str, str] = {
    "discussion:socratic": (
        f"{_GROUNDING_RULES} Teach by Socratic questioning: lead the learner with "
        "probing questions toward the answer rather than stating it outright."
    ),
    "discussion:euclidean": (
        f"{_GROUNDING_RULES} Explain directly and precisely, building from "
        "definitions to conclusions like a geometric proof. Be concise."
    ),
    "scenario": (
        f"{_GROUNDING_RULES} The learner is working through an applied scenario. "
        "Respond in character as the scenario facilitator; do not reveal the "
        "evaluation rubric."
    ),
}


def _no_context_response() -> AssistantChatResponse:
    return AssistantChatResponse(
        answer=(
            "I couldn't find anything in this workspace's material that covers "
            "that. Try rephrasing, or ask about a topic from the source."
        ),
        grounded=False,
        citations=[],
    )


def _render_context(chunks: list[RetrievedChunk]) -> str:
    lines = []
    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"[{index}] ({chunk.label}) {chunk.text}")
    return "\n\n".join(lines)


class AssistantService:
    def __init__(
        self,
        *,
        retrieval: RetrievalService,
        assessments: AssessmentRepository,
        chat_model: str | None = None,
        openai_client: OpenAIClient | None = None,
    ) -> None:
        self.retrieval = retrieval
        self.assessments = assessments
        self.chat_model = chat_model
        self._openai_client = openai_client

    @property
    def openai_client(self) -> OpenAIClient:
        if self._openai_client is None:
            self._openai_client = OpenAIClient()
        return self._openai_client

    async def chat(
        self,
        request: AssistantChatRequest,
        workspace_id: str,
    ) -> AssistantChatResponse:
        latest_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )

        chunks = await self.retrieval.retrieve(
            latest_user,
            workspace_id,
            source_ids=request.source_ids,
        )
        if not chunks:
            return _no_context_response()

        system_prompt = self._system_prompt(request)
        context_block = _render_context(chunks)
        history = [m.model_dump() for m in request.messages]
        # SECURITY: Retrieved evidence is injected as a user turn so the chat
        # API can keep a single message list. Treat SOURCE MATERIAL as untrusted
        # grounding data, not instructions (same role channel as the learner).
        history.insert(
            max(len(history) - 1, 0),
            {"role": "user", "content": f"SOURCE MATERIAL:\n{context_block}"},
        )

        result = await asyncio.to_thread(
            self.openai_client.complete_text,
            system_prompt=system_prompt,
            messages=history,
            model=self.chat_model,
            temperature=0.3,
        )
        answer = result.content["text"]

        evaluation = None
        if request.mode == "scenario" and request.scenario_id:
            evaluation = await self._evaluate_scenario(
                request.scenario_id, workspace_id, latest_user, context_block
            )

        return AssistantChatResponse(
            answer=answer,
            grounded=True,
            citations=[Citation(**chunk.to_citation()) for chunk in chunks],
            evaluation=evaluation,
        )

    def _system_prompt(self, request: AssistantChatRequest) -> str:
        if request.mode == "discussion":
            submode = request.submode or "socratic"
            return SYSTEM_PROMPTS[f"discussion:{submode}"]
        return SYSTEM_PROMPTS["scenario"]

    async def _evaluate_scenario(
        self,
        scenario_id: str,
        workspace_id: str,
        learner_answer: str,
        context_block: str,
    ) -> ScenarioEvaluation | None:
        scenario = await self.assessments.get_scenario(scenario_id, workspace_id)
        if not scenario:
            return None

        criteria = scenario.get("evaluation_criteria") or []
        rubric = scenario.get("rubric")

        grader_prompt = (
            "You are grading a learner's response to an applied scenario. "
            "Judge it ONLY against the evaluation criteria and rubric provided. "
            "Return JSON with keys: passed (bool), score (0-1 float), feedback "
            "(string), met_criteria (string[]), missed_criteria (string[])."
        )
        payload = {
            "scenario_prompt": scenario.get("prompt"),
            "evaluation_criteria": criteria,
            "rubric": rubric,
            "source_material": context_block,
            "learner_answer": learner_answer,
        }

        result = await asyncio.to_thread(
            self.openai_client.complete_json,
            system_prompt=grader_prompt,
            user_prompt=json.dumps(payload),
            model=self.chat_model,
        )
        return _parse_evaluation(result.content)


def _parse_evaluation(content: dict[str, Any]) -> ScenarioEvaluation:
    return ScenarioEvaluation(
        passed=bool(content.get("passed", False)),
        score=content.get("score"),
        feedback=str(content.get("feedback", "")),
        met_criteria=list(content.get("met_criteria", [])),
        missed_criteria=list(content.get("missed_criteria", [])),
    )
