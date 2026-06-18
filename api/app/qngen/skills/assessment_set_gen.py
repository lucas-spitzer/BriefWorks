from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.qngen.canonical_context import ConceptCard, format_concepts_for_llm, format_concept_segments_for_llm
from app.qngen.context import format_json_block
from app.qngen.skills.assessment_set_models import AssessmentBatchOutput, AssessmentSetGenOutput
from app.services.openai_client import OpenAIClient

SYSTEM_PROMPT = """You generate linked assessment items from canonical wiki concepts.

Rules:
- Ground every item in the provided concept cards and evidence segments only.
- Use preferred_label verbatim when a term appears in an item.
- Definitions and answers must align with the provided wiki definition.
- Do not invent concepts outside the batch.
- Every item must cite wiki_ids_cited and source_chunk_ids from the batch context.
- Return valid JSON with a top-level "items" array only.

Item types and subtypes:
- flashcard: term_definition (default), basic, or cloze
- quiz: multiple_choice (default), true_false_correction, or multiple_select
- scenario: decision_prompt (default) or rubric_response

Per concept in the batch:
- Generate 1 flashcard (term_definition preferred)
- Generate 1 quiz (multiple_choice preferred)
- For essential concepts only: generate 1 scenario when scenarios are requested

Difficulty must be easy, medium, or hard."""

USER_TEMPLATE = """Source metadata:
{source_metadata}

Assessment types requested: {assessment_types}

Canonical concepts for this batch:
{concepts_json}

Evidence segments:
{segments_json}

Return JSON:
{{
  "items": [
    {{
      "item_id": "uuid-string",
      "type": "flashcard|quiz|scenario",
      "subtype": "term_definition|multiple_choice|decision_prompt|...",
      "difficulty": "easy|medium|hard",
      "wiki_ids_cited": ["wiki-id"],
      "source_chunk_ids": ["segment-id"],
      "tags": ["tag"],
      "front": "flashcard front",
      "back": "flashcard back",
      "question": "quiz question",
      "choices": ["A", "B", "C", "D"],
      "correct_answer": "answer",
      "explanation": "why correct",
      "situation": "scenario background",
      "task": "what learner must do",
      "expected_response_elements": ["element"],
      "rubric": {{"excellent": "...", "satisfactory": "...", "poor": "..."}}
    }}
  ]
}}

Only include fields relevant to each item type. Omit flashcard fields from quiz/scenario items, etc."""


class AssessmentSetGenSkill:
    def __init__(self, *, openai_client: OpenAIClient | None = None) -> None:
        settings = get_settings()
        self.openai_client = openai_client or OpenAIClient(model=settings.qngen_model)

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        concept_batches: list[list[ConceptCard]],
        assessment_types: list[str],
    ) -> tuple[AssessmentSetGenOutput, dict[str, Any]]:
        if not concept_batches:
            raise RuntimeError("At least one concept batch is required for assessment generation.")

        output = AssessmentSetGenOutput()
        token_usage: dict[str, int] = {}
        model = self.openai_client.model

        for batch in concept_batches:
            batch_output, execution = self._run_batch(
                source_metadata=source_metadata,
                concepts=batch,
                assessment_types=assessment_types,
            )
            model = execution["model"]
            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value
            output.add_batch(batch_output)

        return output, {
            "model": model,
            "token_usage": token_usage,
            "batch_count": len(concept_batches),
        }

    def _run_batch(
        self,
        *,
        source_metadata: dict[str, Any],
        concepts: list[ConceptCard],
        assessment_types: list[str],
    ) -> tuple[AssessmentBatchOutput, dict[str, Any]]:
        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=format_json_block(source_metadata),
                assessment_types=json.dumps(assessment_types),
                concepts_json=format_concepts_for_llm(concepts),
                segments_json=format_concept_segments_for_llm(concepts),
            ),
        )
        raw_items = result.content.get("items", [])
        filtered_items = self._filter_items_by_type(raw_items, assessment_types, concepts)
        batch_output = AssessmentBatchOutput(items=filtered_items)

        return batch_output, {
            "model": result.model,
            "token_usage": result.token_usage,
        }

    def _filter_items_by_type(
        self,
        items: list[dict[str, Any]],
        assessment_types: list[str],
        concepts: list[ConceptCard],
    ) -> list[dict[str, Any]]:
        type_map = {
            "flashcards": "flashcard",
            "quizzes": "quiz",
            "scenarios": "scenario",
        }
        allowed_types = {type_map[artifact] for artifact in assessment_types if artifact in type_map}
        essential_wiki_ids = {
            concept.wiki_id for concept in concepts if concept.importance == "essential"
        }

        filtered: list[dict[str, Any]] = []
        for item in items:
            item_type = item.get("type")
            if item_type not in allowed_types:
                continue
            if item_type == "scenario":
                wiki_cited = set(item.get("wiki_ids_cited") or [])
                if wiki_cited and not wiki_cited.intersection(essential_wiki_ids):
                    continue
            filtered.append(item)

        return filtered
