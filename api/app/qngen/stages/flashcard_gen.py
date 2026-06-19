from __future__ import annotations

from typing import Any

from app.qngen.context import build_wiki_context, compact_segments, format_json_block
from app.qngen.stages.models import FlashcardGenOutput
from app.services.openai_client import OpenAIClient

SYSTEM_PROMPT = """You generate memorization flashcards from source documents.

Rules:
- Ground every card in the provided source segments.
- Use canonical wiki terminology exactly when wiki entries are provided.
- Front: concise prompt or term. Back: accurate answer grounded in the source.
- Include difficulty: easy, medium, or hard.
- Add short tags when helpful.
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
  "flashcards": [
    {{
      "front": "question or term",
      "back": "answer",
      "difficulty": "easy|medium|hard",
      "tags": ["tag"],
      "wiki_ids_cited": ["wiki-id"],
      "segment_ids_used": ["segment-id"]
    }}
  ]
}}"""


class FlashcardGenStage:
    def __init__(self, *, openai_client: OpenAIClient | None = None) -> None:
        self.openai_client = openai_client or OpenAIClient()

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
    ) -> tuple[FlashcardGenOutput, dict[str, Any]]:
        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=format_json_block(source_metadata),
                wiki_entries=format_json_block(build_wiki_context(wiki_entries)),
                segments_json=format_json_block(compact_segments(segments)),
            ),
        )
        output = FlashcardGenOutput.model_validate(result.content)

        return output, {
            "model": result.model,
            "token_usage": result.token_usage,
        }
