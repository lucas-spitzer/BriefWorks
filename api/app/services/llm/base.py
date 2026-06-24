from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from app.llm_defaults import HAIKU_45_MODEL


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
