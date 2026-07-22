from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMCompletionResult:
    """Provider-neutral result of a single structured (JSON) completion.

    ``token_usage`` is normalized to ``input_tokens`` / ``output_tokens`` /
    ``total_tokens`` regardless of provider, so the billing layer never needs to
    know which provider produced it.
    """

    content: dict[str, Any]
    model: str
    provider: str = "unknown"
    token_usage: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every provider client implements.

    Keeping this surface small is what makes the rest of the system provider-
    and model-agnostic: stages type against this protocol, never a concrete
    provider client.
    """

    provider: str
    model: str

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> LLMCompletionResult:
        """Return a single JSON-object completion.

        Implementations must coerce the model's output into a ``dict`` or raise.
        """
        ...

    def complete_json_with_web_search(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_searches: int = 5,
    ) -> LLMCompletionResult:
        """Return a JSON-object completion where the model may issue web searches.

        ``token_usage`` additionally carries ``web_search_requests`` so the
        billing layer can price searches separately from tokens.
        """
        ...
