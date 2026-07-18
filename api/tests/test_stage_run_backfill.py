from app.services.stage_run_backfill import (
    backfill_fields_for_stage_run,
    enrich_stage_run_row,
    execution_from_stage_run,
)


def test_enrich_stage_run_row_backfills_parse_cost() -> None:
    enriched = enrich_stage_run_row(
        {
            "stage_id": "parse",
            "model": "llamaparse",
            "cost_usd": 0,
            "token_usage": {},
            "output": {"page_count": 10},
            "api_usage": {},
        },
    )

    assert enriched["cost_usd"] > 0
    assert enriched["api_usage"]["totals"]["credit_count"] == 10


def test_enrich_stage_run_row_fills_missing_cost() -> None:
    enriched = enrich_stage_run_row(
        {
            "stage_id": "elevenreader-ebook",
            "model": "gpt-4o-mini",
            "cost_usd": 0,
            "token_usage": {"input_tokens": 500, "output_tokens": 100},
            "api_usage": {},
        },
    )

    assert enriched["cost_usd"] > 0
    assert enriched["api_usage"]["totals"]["input_tokens"] == 500


def test_execution_from_parse_infers_page_credits() -> None:
    execution = execution_from_stage_run(
        {
            "stage_id": "parse",
            "model": "llamaparse",
            "token_usage": {},
            "output": {"page_count": 24},
        },
    )

    assert execution["page_count"] == 24


def test_backfill_fields_from_existing_token_usage() -> None:
    fields = backfill_fields_for_stage_run(
        {
            "stage_id": "deconstruct-document",
            "model": "gpt-4o-mini",
            "token_usage": {
                "input_tokens": 66471,
                "output_tokens": 10249,
            },
        },
    )

    assert fields["cost_usd"] > 0
    assert fields["api_usage"]["totals"]["input_tokens"] == 66471
    assert fields["api_usage"]["totals"]["output_tokens"] == 10249


def test_backfill_fields_for_mathesys_llm_token_usage() -> None:
    fields = backfill_fields_for_stage_run(
        {
            "stage_id": "elevenreader-ebook",
            "model": "gpt-4o-mini",
            "token_usage": {
                "input_tokens": 12_000,
                "output_tokens": 3_000,
            },
        },
    )

    assert fields["cost_usd"] > 0
    assert fields["api_usage"]["totals"]["input_tokens"] == 12_000
    assert fields["api_usage"]["totals"]["output_tokens"] == 3_000


