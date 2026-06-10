from __future__ import annotations

from typing import Any

from app.qngen.context import build_wiki_context, compact_segments, format_json_block
from app.qngen.skills.models import QuizGenOutput
from app.services.openai_client import OpenAIClient

SYSTEM_PROMPT = """You generate quiz questions that test understanding of source documents.

Rules:
- Ground every question in the provided source segments.
- Use canonical wiki terminology exactly when wiki entries are provided.
- Prefer multiple_choice with 4 options when possible; true_false and short_answer are allowed.
- Provide a clear correct_answer and brief explanation.
- Include difficulty: easy, medium, or hard.
- Cite wiki_ids_cited and segment_ids_used from the provided context.
- Return valid JSON only."""

USER_TEMPLATE = """Source metadata:
{source_metadata}

Canonical wiki entries:
{wiki_entries}

Source segments:
{segments_json}

Return JSON:
{{
  "questions": [
    {{
      "question": "question text",
      "question_type": "multiple_choice|true_false|short_answer",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "answer",
      "explanation": "why this is correct",
      "difficulty": "easy|medium|hard",
      "wiki_ids_cited": ["wiki-id"],
      "segment_ids_used": ["segment-id"]
    }}
  ]
}}"""


class QuizGenSkill:
    def __init__(self, *, openai_client: OpenAIClient | None = None) -> None:
        self.openai_client = openai_client or OpenAIClient()

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
    ) -> tuple[QuizGenOutput, dict[str, Any]]:
        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=format_json_block(source_metadata),
                wiki_entries=format_json_block(build_wiki_context(wiki_entries)),
                segments_json=format_json_block(compact_segments(segments)),
            ),
        )
        output = QuizGenOutput.model_validate(result.content)

        return output, {
            "model": result.model,
            "token_usage": result.token_usage,
        }
