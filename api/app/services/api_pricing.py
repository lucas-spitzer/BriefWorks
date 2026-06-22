from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenRates:
    input_per_million: float
    output_per_million: float


@dataclass(frozen=True)
class CharacterRates:
    per_thousand: float


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

# ElevenLabs subscription credits are billed per character; we call them tokens in
# the console. Default: $220 / 1.2M credits per year ≈ $0.00018333 per token.
ELEVENLABS_PRICE_PER_TOKEN = _float_env("ELEVENLABS_PRICE_PER_TOKEN", 0.00018333)

SPEECHIFY_RATES = CharacterRates(
    per_thousand=_float_env("SPEECHIFY_PRICE_PER_1K_CHARS", 0.10),
)

TAVILY_PRICE_PER_CREDIT = _float_env("TAVILY_PRICE_PER_CREDIT", 0.008)

LLAMAPARSE_PRICE_PER_CREDIT = _float_env("LLAMAPARSE_PRICE_PER_CREDIT", 0.00125)


def _round_usd(value: float) -> float:
    return round(value, 6)


def openai_rates_for_model(model: str | None) -> TokenRates:
    normalized = (model or "").strip().lower()

    if normalized in OPENAI_MODEL_RATES:
        return OPENAI_MODEL_RATES[normalized]

    for key, rates in OPENAI_MODEL_RATES.items():
        if normalized.startswith(key):
            return rates

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


def cost_elevenlabs_usage(
    *,
    model_id: str | None,
    character_count: int,
    request_count: int = 1,
) -> dict[str, Any]:
    total = character_count * ELEVENLABS_PRICE_PER_TOKEN

    return {
        "provider": "elevenlabs",
        "model": model_id or "unknown",
        "token_count": character_count,
        "character_count": character_count,
        "request_count": request_count,
        "cost_usd": _round_usd(total),
    }


def cost_speechify_usage(
    *,
    model: str | None,
    character_count: int,
) -> dict[str, Any]:
    total = (character_count / 1_000) * SPEECHIFY_RATES.per_thousand

    return {
        "provider": "speechify",
        "model": model or "unknown",
        "character_count": character_count,
        "cost_usd": _round_usd(total),
    }


def cost_tavily_usage(*, search_count: int) -> dict[str, Any]:
    credit_count = search_count
    total = credit_count * TAVILY_PRICE_PER_CREDIT

    return {
        "provider": "tavily",
        "search_count": search_count,
        "credit_count": credit_count,
        "cost_usd": _round_usd(total),
    }


def cost_llamaparse_usage(*, credit_count: int) -> dict[str, Any]:
    total = credit_count * LLAMAPARSE_PRICE_PER_CREDIT

    return {
        "provider": "llamaparse",
        "credit_count": credit_count,
        "cost_usd": _round_usd(total),
    }
