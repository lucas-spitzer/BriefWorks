from __future__ import annotations

import contextvars
from dataclasses import dataclass

from app.config import get_settings
from app.services.llm.anthropic_client import AnthropicClient
from app.services.llm.base import LLMClient
from app.services.llm.openai_adapter import OpenAILLMClient
from app.services.llm.reasoning import ReasoningSettings

_BUILDERS = {
    "anthropic": lambda model, reasoning: AnthropicClient(model=model, reasoning=reasoning),
    "openai": lambda model, reasoning: OpenAILLMClient(model=model, reasoning=reasoning),
}


@dataclass(frozen=True)
class ActionOverride:
    """A workspace's chosen provider/model (and reasoning) for one stage action."""

    provider: str
    model: str
    reasoning: ReasoningSettings | None = None


# Per-run, workspace-scoped overrides. The worker sets this for the duration of a
# production run so every get_llm_client call — including those resolved lazily
# inside stages — picks up the workspace's chosen models without threading the
# workspace id through every signature. Empty by default, so behavior is
# unchanged when no workspace settings exist.
_workspace_overrides: contextvars.ContextVar[dict[str, ActionOverride]] = (
    contextvars.ContextVar("workspace_llm_overrides", default={})
)


def set_workspace_overrides(
    overrides: dict[str, ActionOverride],
) -> contextvars.Token[dict[str, ActionOverride]]:
    """Install workspace overrides; pass the returned token to reset afterwards."""
    return _workspace_overrides.set(overrides)


def reset_workspace_overrides(
    token: contextvars.Token[dict[str, ActionOverride]],
) -> None:
    _workspace_overrides.reset(token)


def overrides_from_rows(rows: list[dict[str, object]]) -> dict[str, ActionOverride]:
    """Build the action→override map from workspace_stage_settings rows.

    Permissive by design: a stored model that isn't in the curated catalog is
    still honored, since the point of per-workspace settings is to repoint a
    stage at a newly released model without a code change. Only rows for a
    provider we cannot build a client for are dropped.
    """
    overrides: dict[str, ActionOverride] = {}

    for row in rows:
        action = str(row.get("stage_action") or "").strip()
        provider = str(row.get("provider") or "").strip().lower()
        model = str(row.get("model") or "").strip()

        if not action or provider not in _BUILDERS or not model:
            continue

        overrides[action] = ActionOverride(
            provider=provider,
            model=model,
            reasoning=_reasoning_from_row(row),
        )

    return overrides


def _reasoning_from_row(row: dict[str, object]) -> ReasoningSettings | None:
    effort_raw = row.get("reasoning_effort")
    effort = str(effort_raw).strip().lower() if effort_raw else None

    tokens_raw = row.get("reasoning_tokens")
    try:
        tokens = int(tokens_raw) if tokens_raw else None
    except (TypeError, ValueError):
        tokens = None

    if not effort and not tokens:
        return None

    return ReasoningSettings(effort=effort or None, thinking_budget_tokens=tokens)


def resolve_action(action: str) -> tuple[str, str]:
    """Return the (provider, model) for an action.

    Resolution order: workspace override → env var → in-code registry default.
    """
    override = _workspace_overrides.get().get(action)
    if override is not None:
        return override.provider, override.model

    action_settings = get_settings().llm.resolve_action(action)
    return action_settings.provider, action_settings.model


def get_llm_client(action: str) -> LLMClient:
    """Build the LLM client configured for an action."""
    provider, model = resolve_action(action)
    builder = _BUILDERS.get(provider)

    if builder is None:
        raise RuntimeError(
            f"Unknown LLM provider '{provider}' for action '{action}'. "
            f"Supported providers: {', '.join(sorted(_BUILDERS))}.",
        )

    override = _workspace_overrides.get().get(action)
    reasoning = override.reasoning if override is not None else None

    return builder(model, reasoning)
