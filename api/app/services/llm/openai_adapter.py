from __future__ import annotations

from app.services.llm.base import LLMCompletionResult
from app.services.llm.reasoning import ReasoningSettings
from app.services.openai_client import OpenAIClient


class OpenAILLMClient:
    """Adapt the existing ``OpenAIClient`` to the ``LLMClient`` protocol.

    Reuses the established OpenAI logic verbatim and only adds the ``provider``
    tag the billing layer needs to pick the right rate table.
    """

    provider = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        reasoning: ReasoningSettings | None = None,
    ) -> None:
        self._client = OpenAIClient(
            api_key=api_key,
            model=model,
            reasoning_effort=reasoning.effort if reasoning else None,
        )
        self.model = self._client.model

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> LLMCompletionResult:
        result = self._client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
        )

        return LLMCompletionResult(
            content=result.content,
            model=result.model,
            provider=self.provider,
            token_usage=result.token_usage,
        )

    def complete_json_with_web_search(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_searches: int = 5,
    ) -> LLMCompletionResult:
        result = self._client.complete_json_with_web_search(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_searches=max_searches,
        )

        return LLMCompletionResult(
            content=result.content,
            model=result.model,
            provider=self.provider,
            token_usage=result.token_usage,
        )
