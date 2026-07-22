"""One-shot reader term definitions (contextual passage sense or general sense)."""

from __future__ import annotations

import asyncio
from app.models.reader_define import ReaderDefineRequest, ReaderDefineResponse
from app.services.api_pricing import cost_llm_usage
from app.services.llm import get_llm_client
from app.services.llm.base import LLMClient


class ReaderDefineError(ValueError):
    """Raised when a define request is invalid or the model returns unusable output."""


CONTEXTUAL_SYSTEM_PROMPT = """\
You write short learner-facing definitions for a term as it is used in a passage.

Rules:
- Define the term in the sense implied by the surrounding paragraphs.
- Prefer the passage sense over a generic textbook sense when they conflict.
- Keep the definition to a single concise sentence whenever possible.
- Do not invent facts that contradict the passage.
- Return JSON only: {"definition": string}
"""

GENERAL_SYSTEM_PROMPT = """\
You write short general (dictionary-style) definitions for a term, guided by its sentence.

Rules:
- Give the common meaning that fits the sentence, not a passage-specific gloss.
- Keep the definition to a single concise sentence whenever possible.
- Do not claim the definition is grounded in a specific source passage.
- Return JSON only: {"definition": string}
"""


class ReaderDefineService:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client

    @property
    def llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = get_llm_client("reader_define")
        return self._llm_client

    async def define(self, request: ReaderDefineRequest) -> ReaderDefineResponse:
        term = request.term.strip()
        if not term:
            raise ReaderDefineError("Term is required.")

        if request.mode == "contextual":
            current = (request.current_paragraph or "").strip()
            if not current:
                raise ReaderDefineError(
                    "Contextual definitions require the current paragraph.",
                )
            system_prompt = CONTEXTUAL_SYSTEM_PROMPT
            user_prompt = (
                f"TERM: {term}\n\n"
                f"PREVIOUS PARAGRAPH:\n{(request.prev_paragraph or '').strip() or '(none)'}\n\n"
                f"CURRENT PARAGRAPH:\n{current}\n\n"
                f"NEXT PARAGRAPH:\n{(request.next_paragraph or '').strip() or '(none)'}"
            )
        else:
            system_prompt = GENERAL_SYSTEM_PROMPT
            sentence = (request.sentence or "").strip()
            user_prompt = (
                f"TERM: {term}\n\n"
                f"SENTENCE:\n{sentence or '(not provided)'}\n\n"
                f"CURRENT PARAGRAPH:\n{(request.current_paragraph or '').strip() or '(none)'}"
            )

        result = await asyncio.to_thread(
            self.llm_client.complete_json,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        definition = result.content.get("definition")
        if not isinstance(definition, str) or not definition.strip():
            raise ReaderDefineError("The model returned no definition.")

        # Record cost when usage is present; ignore pricing gaps.
        usage = result.token_usage or {}
        cost_llm_usage(
            provider=getattr(result, "provider", "openai") or "openai",
            model=result.model,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
        )

        return ReaderDefineResponse(
            term=term,
            definition=definition.strip(),
            mode=request.mode,
            provenance=request.mode,
        )


def get_reader_define_service() -> ReaderDefineService:
    return ReaderDefineService()
