from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.models.reader_define import ReaderDefineRequest
from app.services.llm.base import LLMCompletionResult
from app.services.reader_define import ReaderDefineError, ReaderDefineService


class FakeLLM:
    provider = "openai"
    model = "gpt-test"

    def __init__(self, definition: str = "A short definition.") -> None:
        self.definition = definition
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "model": model,
            },
        )
        return LLMCompletionResult(
            content={"definition": self.definition},
            model=self.model,
            provider=self.provider,
            token_usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        )


def test_contextual_define_requires_current_paragraph() -> None:
    service = ReaderDefineService(llm_client=FakeLLM())  # type: ignore[arg-type]
    request = ReaderDefineRequest(term="tempo", mode="contextual", current_paragraph="  ")

    with pytest.raises(ReaderDefineError, match="current paragraph"):
        asyncio.run(service.define(request))


def test_contextual_define_includes_neighbors_in_prompt() -> None:
    llm = FakeLLM("Speed of decision cycles.")
    service = ReaderDefineService(llm_client=llm)  # type: ignore[arg-type]
    request = ReaderDefineRequest(
        term="tempo",
        mode="contextual",
        prev_paragraph="Earlier context.",
        current_paragraph="They increased tempo in the fight.",
        next_paragraph="Later result.",
    )

    result = asyncio.run(service.define(request))

    assert result.definition == "Speed of decision cycles."
    assert result.mode == "contextual"
    assert result.provenance == "contextual"
    assert "PREVIOUS PARAGRAPH:\nEarlier context." in llm.calls[0]["user_prompt"]
    assert "CURRENT PARAGRAPH:\nThey increased tempo in the fight." in llm.calls[0]["user_prompt"]
    assert "NEXT PARAGRAPH:\nLater result." in llm.calls[0]["user_prompt"]
    assert "learner-facing" in llm.calls[0]["system_prompt"] or "passage" in llm.calls[0]["system_prompt"]


def test_general_define_uses_sentence_and_general_prompt() -> None:
    llm = FakeLLM("A general pace or rate.")
    service = ReaderDefineService(llm_client=llm)  # type: ignore[arg-type]
    request = ReaderDefineRequest(
        term="tempo",
        mode="general",
        sentence="The orchestra kept a steady tempo.",
        current_paragraph="Optional paragraph.",
    )

    result = asyncio.run(service.define(request))

    assert result.provenance == "general"
    assert "SENTENCE:\nThe orchestra kept a steady tempo." in llm.calls[0]["user_prompt"]
    assert "dictionary-style" in llm.calls[0]["system_prompt"]


def test_define_rejects_empty_model_definition() -> None:
    llm = FakeLLM("   ")
    service = ReaderDefineService(llm_client=llm)  # type: ignore[arg-type]
    request = ReaderDefineRequest(
        term="tempo",
        mode="general",
        sentence="x",
    )

    with pytest.raises(ReaderDefineError, match="no definition"):
        asyncio.run(service.define(request))
