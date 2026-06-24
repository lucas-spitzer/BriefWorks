"""Curated catalog of selectable LLM models.

Hand-maintained, not fetched from providers: adding a newly released model is a
one-line edit here, which is the whole point — surface swappable models without
code changes elsewhere.

- ``capability_tier`` is a curated 1 (lightest) .. 5 (most capable) judgment.
  No in-repo benchmark exists, so this is intentionally coarse guidance for the
  settings UI's "capability vs cost" view, not a measured score.
- ``input_per_million`` / ``output_per_million`` are indicative published list
  prices in USD per million tokens. They are ``None`` when not reliably known.
  They feed billing only as a *fallback* in app.services.api_pricing for models
  absent from its env-overridable rate tables; an env override always wins.

Kept dependency-light (stdlib + app.llm_defaults) so app.services.api_pricing can
import it without an import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm_defaults import DEFAULT_OPENAI_MODEL, HAIKU_45_MODEL


@dataclass(frozen=True)
class CatalogModel:
    model: str
    provider: str
    display_name: str
    capability_tier: int
    supports_reasoning: bool
    reasoning_modes: tuple[str, ...]
    context_window: int | None = None
    input_per_million: float | None = None
    output_per_million: float | None = None


# Prices are USD per million tokens (standard on-demand, paid tier), from the
# June 2026 pricing snapshot. Only providers with a working client (OpenAI,
# Anthropic) are listed — adding Google here would let the UI pick a model the
# factory cannot build. context_window is left None where not reliably known.
MODEL_CATALOG: tuple[CatalogModel, ...] = (
    # --- Anthropic ---
    CatalogModel(
        model="claude-opus-4-8",
        provider="anthropic",
        display_name="Claude Opus 4.8",
        capability_tier=5,
        supports_reasoning=True,
        reasoning_modes=("adaptive",),
        context_window=200_000,
        input_per_million=5.00,
        output_per_million=25.00,
    ),
    CatalogModel(
        model="claude-sonnet-4-6",
        provider="anthropic",
        display_name="Claude Sonnet 4.6",
        capability_tier=4,
        supports_reasoning=True,
        reasoning_modes=("adaptive",),
        context_window=200_000,
        input_per_million=3.00,
        output_per_million=15.00,
    ),
    CatalogModel(
        model=HAIKU_45_MODEL,
        provider="anthropic",
        display_name="Claude Haiku 4.5",
        capability_tier=3,
        supports_reasoning=True,
        reasoning_modes=("budget",),
        context_window=200_000,
        input_per_million=1.00,
        output_per_million=5.00,
    ),
    # --- OpenAI ---
    CatalogModel(
        model="gpt-5.5",
        provider="openai",
        display_name="GPT-5.5",
        capability_tier=5,
        supports_reasoning=True,
        reasoning_modes=("effort",),
        context_window=None,
        input_per_million=5.00,
        output_per_million=30.00,
    ),
    CatalogModel(
        model="gpt-5.4",
        provider="openai",
        display_name="GPT-5.4",
        capability_tier=4,
        supports_reasoning=True,
        reasoning_modes=("effort",),
        context_window=None,
        input_per_million=2.50,
        output_per_million=15.00,
    ),
    CatalogModel(
        model="gpt-5.4-mini",
        provider="openai",
        display_name="GPT-5.4 mini",
        capability_tier=3,
        supports_reasoning=True,
        reasoning_modes=("effort",),
        context_window=None,
        input_per_million=0.75,
        output_per_million=4.50,
    ),
    CatalogModel(
        model="gpt-4o",
        provider="openai",
        display_name="GPT-4o",
        capability_tier=3,
        supports_reasoning=False,
        reasoning_modes=(),
        context_window=128_000,
        input_per_million=2.50,
        output_per_million=10.00,
    ),
    CatalogModel(
        model=DEFAULT_OPENAI_MODEL,
        provider="openai",
        display_name="GPT-4o mini",
        capability_tier=2,
        supports_reasoning=False,
        reasoning_modes=(),
        context_window=128_000,
        input_per_million=0.15,
        output_per_million=0.60,
    ),
)


def get_catalog_model(model: str | None) -> CatalogModel | None:
    """Match a provider model id to a catalog entry (exact, then longest prefix)."""
    normalized = (model or "").strip().lower()

    if not normalized:
        return None

    for entry in MODEL_CATALOG:
        if entry.model.lower() == normalized:
            return entry

    # Longest prefix first so "gpt-4o-mini-..." beats "gpt-4o".
    for entry in sorted(MODEL_CATALOG, key=lambda e: len(e.model), reverse=True):
        if normalized.startswith(entry.model.lower()):
            return entry

    return None


SELECTABLE_PROVIDERS: frozenset[str] = frozenset({"openai", "anthropic"})


def validate_selection(provider: str | None, model: str | None) -> str | None:
    """Validate a workspace's stage selection; return an error message or None.

    Permits models absent from the curated catalog (new releases should be
    selectable without a code change), but rejects unsupported providers, empty
    models, and a known model paired with the wrong provider.
    """
    normalized_provider = (provider or "").strip().lower()
    normalized_model = (model or "").strip()

    if normalized_provider not in SELECTABLE_PROVIDERS:
        return f"Unsupported provider '{provider}'."

    if not normalized_model:
        return "Model is required."

    entry = get_catalog_model(normalized_model)
    if entry is not None and entry.provider != normalized_provider:
        return (
            f"Model '{normalized_model}' belongs to provider '{entry.provider}', "
            f"not '{normalized_provider}'."
        )

    return None


def catalog_list_price(model: str | None) -> tuple[float, float] | None:
    """Indicative (input, output) USD per million tokens, or None if unknown."""
    entry = get_catalog_model(model)

    if entry is None or entry.input_per_million is None or entry.output_per_million is None:
        return None

    return (entry.input_per_million, entry.output_per_million)
