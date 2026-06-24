from app.services.api_pricing import (
    cost_anthropic_usage,
    cost_elevenlabs_usage,
    cost_llamaparse_usage,
    cost_openai_usage,
    cost_speechify_usage,
)
from app.services.stage_run_billing import (
    build_api_usage,
    stage_run_completion_fields,
    tts_call_from_manifest,
)


def test_openai_cost_uses_model_rates() -> None:
    call = cost_openai_usage(model="gpt-4o-mini", input_tokens=1_000_000, output_tokens=500_000)

    assert call["input_cost_usd"] == 0.15
    assert call["output_cost_usd"] == 0.3
    assert call["cost_usd"] == 0.45


def test_build_api_usage_from_execution() -> None:
    usage = build_api_usage(
        {
            "model": "gpt-4o-mini",
            "token_usage": {
                "input_tokens": 10_000,
                "output_tokens": 2_000,
            },
        },
    )

    assert len(usage["calls"]) == 1
    assert usage["totals"]["input_tokens"] == 10_000
    assert usage["totals"]["output_tokens"] == 2_000
    assert usage["totals"]["cost_usd"] > 0


def test_tts_call_from_manifest() -> None:
    eleven_call = tts_call_from_manifest(
        {
            "model_id": "eleven_v3",
            "character_count": 2_000,
            "tts_request_count": 2,
        },
    )
    speechify_call = tts_call_from_manifest(
        {
            "model": "simba-english",
            "character_count": 1_000,
        },
    )

    assert eleven_call is not None
    assert eleven_call["provider"] == "elevenlabs"
    assert eleven_call["request_count"] == 2
    assert eleven_call["token_count"] == 2_000
    assert eleven_call["cost_usd"] == round(2_000 * 0.00018333, 6)

    assert speechify_call is not None
    assert speechify_call["provider"] == "speechify"


def test_cost_elevenlabs_usage_per_token() -> None:
    call = cost_elevenlabs_usage(model_id="eleven_v3", character_count=1_200_000)

    assert call["token_count"] == 1_200_000
    assert call["cost_usd"] == round(1_200_000 * 0.00018333, 6)


def test_stage_run_completion_fields() -> None:
    fields = stage_run_completion_fields(
        {
            "model": "gpt-4o-mini",
            "token_usage": {"input_tokens": 100, "output_tokens": 50},
        },
        extra_calls=[cost_speechify_usage(model="simba-english", character_count=500)],
    )

    assert fields["cost_usd"] == fields["api_usage"]["totals"]["cost_usd"]
    assert len(fields["api_usage"]["calls"]) == 2


def test_llamaparse_cost() -> None:
    call = cost_llamaparse_usage(credit_count=80)

    assert call["credit_count"] == 80
    assert call["cost_usd"] == 0.1


def test_build_api_usage_includes_llamaparse_credits() -> None:
    usage = build_api_usage(
        {
            "model": "llamaparse",
            "token_usage": {},
            "page_count": 42,
        },
    )

    assert len(usage["calls"]) == 1
    assert usage["calls"][0]["provider"] == "llamaparse"
    assert usage["totals"]["credit_count"] == 42
    assert usage["totals"]["cost_usd"] == round(42 * 0.00125, 6)


def test_build_api_usage_routes_anthropic_provider() -> None:
    usage = build_api_usage(
        {
            "model": "claude-sonnet-4-6",
            "provider": "anthropic",
            "token_usage": {
                "input_tokens": 10_000,
                "output_tokens": 2_000,
            },
        },
    )

    assert len(usage["calls"]) == 1
    assert usage["calls"][0]["provider"] == "anthropic"
    assert usage["totals"]["cost_usd"] == cost_anthropic_usage(
        model="claude-sonnet-4-6",
        input_tokens=10_000,
        output_tokens=2_000,
    )["cost_usd"]
