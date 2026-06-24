from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReasoningSettings:
    """Provider-neutral reasoning depth for a single stage action.

    Mirrors the two persisted columns on ``workspace_stage_settings``:

    - ``effort`` is the coarse dial (``low`` / ``medium`` / ``high`` …) used by
      OpenAI ``reasoning_effort`` and Anthropic adaptive ``output_config.effort``.
    - ``thinking_budget_tokens`` is the manual token cap used by Anthropic
      budget-mode models (Haiku 4.5 and older).

    Each provider client translates this into its own native parameters; an
    empty instance means "send no reasoning params", preserving today's
    behavior for stages without a workspace override.
    """

    effort: str | None = None
    thinking_budget_tokens: int | None = None

    def is_empty(self) -> bool:
        return not self.effort and not self.thinking_budget_tokens
