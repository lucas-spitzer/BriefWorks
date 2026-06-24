from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.config import get_settings


@dataclass(frozen=True)
class OpenAICompletionResult:
    content: dict[str, Any]
    model: str
    token_usage: dict[str, int]


class OpenAIClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        settings = get_settings()
        resolved_key = api_key or settings.llm.openai_api_key

        if not resolved_key:
            raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")

        self.model = model or settings.llm.openai_model
        self.reasoning_effort = reasoning_effort
        self.client = OpenAI(api_key=resolved_key)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> OpenAICompletionResult:
        request: dict[str, Any] = {
            "model": model or self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        # Sent only when a workspace opts in, so non-reasoning models and the
        # default path issue the exact same request as before.
        if self.reasoning_effort:
            request["reasoning_effort"] = self.reasoning_effort

        response = self.client.chat.completions.create(**request)

        message_content = response.choices[0].message.content

        if not message_content:
            raise RuntimeError("OpenAI returned an empty response.")

        parsed = json.loads(message_content)

        if not isinstance(parsed, dict):
            raise RuntimeError("OpenAI response was not a JSON object.")

        usage = response.usage
        token_usage = {
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }

        return OpenAICompletionResult(
            content=parsed,
            model=response.model,
            token_usage=token_usage,
        )
