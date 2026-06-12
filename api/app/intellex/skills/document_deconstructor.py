from __future__ import annotations

import json
from typing import Any

from app.intellex.ndr_formatting import format_segments_for_llm, split_segments_into_batches
from app.intellex.skills.deconstructor_models import DeconstructedConcept, DocumentDeconstructorOutput
from app.services.openai_client import OpenAIClient

SYSTEM_PROMPT = """You are a knowledge extraction system for BriefWorks.

Your job is DECONSTRUCTION, not summarization. Identify terms and concepts a reader must
understand to comprehend the document. Do not produce lesson narrative or study guides.

For each term or concept:
- Provide a definition grounded in the document text.
- List aliases used in the document.
- List prerequisite concepts by label when helpful.
- Provide pronunciation for acronyms and uncommon terms (plain phonetic English).
- Rate importance: essential, supporting, or contextual.
- Cite evidence using segment_id values from the provided NDR segments.
- Provide confidence from 0.0 to 1.0.

Rules:
- Prefer terms explicitly defined or centrally used in the document.
- Include critical acronyms and doctrinal vocabulary when present.
- Do not duplicate the same concept under different labels; use aliases instead.
- Return valid JSON with a top-level concepts array only."""

USER_TEMPLATE = """Source metadata:
{source_metadata}

NDR segments:
{segments_json}

Existing workspace labels (deduplicate using aliases when these match):
{existing_labels}

Return JSON:
{{ "concepts": [ ... ] }}"""


class DocumentDeconstructorSkill:
    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
        batch_size: int = 40,
    ) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.batch_size = batch_size

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        existing_labels: list[str] | None = None,
    ) -> tuple[DocumentDeconstructorOutput, dict[str, Any]]:
        # SECURITY: NDR segment text is private source material sent to the model
        # for workspace-scoped knowledge extraction only.
        if not segments:
            raise RuntimeError("NDR segments are required for document deconstruction.")

        batches = split_segments_into_batches(segments, batch_size=self.batch_size)
        merged_concepts: dict[str, DeconstructedConcept] = {}
        token_usage: dict[str, int] = {}
        model = self.openai_client.model

        for batch in batches:
            batch_output, execution = self._run_batch(
                source_metadata=source_metadata,
                segments=batch,
                existing_labels=existing_labels or [],
            )
            model = execution["model"]

            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            for concept in batch_output.concepts:
                slug = concept.term_label.strip().lower()
                existing = merged_concepts.get(slug)

                if not existing:
                    merged_concepts[slug] = concept
                    continue

                if concept.importance == "essential" or existing.importance != "essential":
                    merged_concepts[slug] = concept

        return DocumentDeconstructorOutput(concepts=list(merged_concepts.values())), {
            "model": model,
            "token_usage": token_usage,
        }

    def _run_batch(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        existing_labels: list[str],
    ) -> tuple[DocumentDeconstructorOutput, dict[str, Any]]:
        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=json.dumps(source_metadata, indent=2),
                segments_json=format_segments_for_llm(segments),
                existing_labels=json.dumps(existing_labels),
            ),
        )
        output = DocumentDeconstructorOutput.model_validate(result.content)
        return output, {
            "model": result.model,
            "token_usage": result.token_usage,
        }
