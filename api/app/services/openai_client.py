from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


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
    ) -> None:
        resolved_key = api_key or os.getenv("OPENAI_API_KEY")

        if not resolved_key:
            raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")

        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=resolved_key)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> OpenAICompletionResult:
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )

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
