from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.services.llm.model_catalog import catalog_list_price


@dataclass(frozen=True)
class TokenRates:
    input_per_million: float
    output_per_million: float


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    return float(raw)


# Published list prices; override via env when your contract differs.
OPENAI_MODEL_RATES: dict[str, TokenRates] = {
    "gpt-4o-mini": TokenRates(
        input_per_million=_float_env("OPENAI_GPT4O_MINI_INPUT_PER_M", 0.15),
        output_per_million=_float_env("OPENAI_GPT4O_MINI_OUTPUT_PER_M", 0.60),
    ),
    "gpt-4o": TokenRates(
        input_per_million=_float_env("OPENAI_GPT4O_INPUT_PER_M", 2.50),
        output_per_million=_float_env("OPENAI_GPT4O_OUTPUT_PER_M", 10.00),
    ),
}

DEFAULT_OPENAI_RATES = TokenRates(
    input_per_million=_float_env("OPENAI_DEFAULT_INPUT_PER_M", 0.15),
    output_per_million=_float_env("OPENAI_DEFAULT_OUTPUT_PER_M", 0.60),
)

# Placeholder rates — override via env before relying on cost_usd for billing.
ANTHROPIC_MODEL_RATES: dict[str, TokenRates] = {
    "claude-opus-4": TokenRates(
        input_per_million=_float_env("ANTHROPIC_OPUS_INPUT_PER_M", 5.00),
        output_per_million=_float_env("ANTHROPIC_OPUS_OUTPUT_PER_M", 25.00),
    ),
    "claude-sonnet-4": TokenRates(
        input_per_million=_float_env("ANTHROPIC_SONNET_INPUT_PER_M", 3.00),
        output_per_million=_float_env("ANTHROPIC_SONNET_OUTPUT_PER_M", 15.00),
    ),
    "claude-haiku-4": TokenRates(
        input_per_million=_float_env("ANTHROPIC_HAIKU_INPUT_PER_M", 1.00),
        output_per_million=_float_env("ANTHROPIC_HAIKU_OUTPUT_PER_M", 5.00),
    ),
}

DEFAULT_ANTHROPIC_RATES = TokenRates(
    input_per_million=_float_env("ANTHROPIC_DEFAULT_INPUT_PER_M", 3.00),
    output_per_million=_float_env("ANTHROPIC_DEFAULT_OUTPUT_PER_M", 15.00),
)

LLAMAPARSE_PRICE_PER_CREDIT = _float_env("LLAMAPARSE_PRICE_PER_CREDIT", 0.00125)

# Server-side web search is billed per search on top of tokens ($10 / 1k
# searches at both providers' list price).
ANTHROPIC_WEB_SEARCH_PRICE_PER_SEARCH = _float_env("ANTHROPIC_WEB_SEARCH_PRICE_PER_SEARCH", 0.01)
OPENAI_WEB_SEARCH_PRICE_PER_SEARCH = _float_env("OPENAI_WEB_SEARCH_PRICE_PER_SEARCH", 0.01)

# ElevenLabs bills TTS per character; the default approximates the Creator
# tier's effective rate. Override to match your subscription.
ELEVENLABS_PRICE_PER_CHARACTER = _float_env("ELEVENLABS_PRICE_PER_CHARACTER", 0.00018333)


def _round_usd(value: float) -> float:
    return round(value, 6)


def openai_rates_for_model(model: str | None) -> TokenRates:
    normalized = (model or "").strip().lower()

    if normalized in OPENAI_MODEL_RATES:
        return OPENAI_MODEL_RATES[normalized]

    for key, rates in OPENAI_MODEL_RATES.items():
        if normalized.startswith(key):
            return rates

    catalog = catalog_list_price(model)
    if catalog is not None:
        return TokenRates(input_per_million=catalog[0], output_per_million=catalog[1])

    return DEFAULT_OPENAI_RATES


def cost_openai_usage(
    *,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    rates = openai_rates_for_model(model)
    input_cost = (input_tokens / 1_000_000) * rates.input_per_million
    output_cost = (output_tokens / 1_000_000) * rates.output_per_million
    total = input_cost + output_cost

    return {
        "provider": "openai",
        "model": model or "unknown",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": _round_usd(input_cost),
        "output_cost_usd": _round_usd(output_cost),
        "cost_usd": _round_usd(total),
    }


def anthropic_rates_for_model(model: str | None) -> TokenRates:
    normalized = (model or "").strip().lower()

    for key, rates in ANTHROPIC_MODEL_RATES.items():
        if normalized.startswith(key):
            return rates

    catalog = catalog_list_price(model)
    if catalog is not None:
        return TokenRates(input_per_million=catalog[0], output_per_million=catalog[1])

    return DEFAULT_ANTHROPIC_RATES


def cost_anthropic_usage(
    *,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    rates = anthropic_rates_for_model(model)
    input_cost = (input_tokens / 1_000_000) * rates.input_per_million
    output_cost = (output_tokens / 1_000_000) * rates.output_per_million
    total = input_cost + output_cost

    return {
        "provider": "anthropic",
        "model": model or "unknown",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": _round_usd(input_cost),
        "output_cost_usd": _round_usd(output_cost),
        "cost_usd": _round_usd(total),
    }


def cost_llm_usage(
    *,
    provider: str,
    model: str | None,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    if provider == "anthropic":
        return cost_anthropic_usage(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    return cost_openai_usage(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def cost_web_search_usage(*, provider: str, search_count: int) -> dict[str, Any]:
    rate = (
        ANTHROPIC_WEB_SEARCH_PRICE_PER_SEARCH
        if provider == "anthropic"
        else OPENAI_WEB_SEARCH_PRICE_PER_SEARCH
    )

    return {
        "provider": provider,
        "model": "web_search",
        "search_count": search_count,
        "cost_usd": _round_usd(search_count * rate),
    }


def cost_llamaparse_usage(*, credit_count: int) -> dict[str, Any]:
    total = credit_count * LLAMAPARSE_PRICE_PER_CREDIT

    return {
        "provider": "llamaparse",
        "credit_count": credit_count,
        "cost_usd": _round_usd(total),
    }


def cost_elevenlabs_usage(*, model: str | None, character_count: int) -> dict[str, Any]:
    total = character_count * ELEVENLABS_PRICE_PER_CHARACTER

    return {
        "provider": "elevenlabs",
        "model": model or "unknown",
        "character_count": character_count,
        "cost_usd": _round_usd(total),
    }
