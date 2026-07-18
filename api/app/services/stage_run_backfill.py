from __future__ import annotations

import json
from typing import Any

from app.services.stage_run_billing import stage_run_completion_fields


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    return value


def execution_from_stage_run(row: dict[str, Any]) -> dict[str, Any]:
    """Rebuild billing execution metadata from a persisted stage_runs row."""

    token_usage = _parse_json_field(row.get("token_usage") or {})

    if not isinstance(token_usage, dict):
        token_usage = {}

    execution: dict[str, Any] = {
        "model": row.get("model"),
        "token_usage": token_usage,
    }

    if row.get("stage_id") == "parse":
        output = _parse_json_field(row.get("output") or {})

        if isinstance(output, dict) and isinstance(output.get("page_count"), int):
            execution["model"] = execution.get("model") or "llamaparse"
            execution["page_count"] = output["page_count"]

    return execution


def backfill_fields_for_stage_run(row: dict[str, Any]) -> dict[str, Any]:
    execution = execution_from_stage_run(row)
    return stage_run_completion_fields(execution)


def enrich_stage_run_row(row: dict[str, Any]) -> dict[str, Any]:
    """Fill in billing fields on read when older runs predate cost tracking."""

    if float(row.get("cost_usd") or 0) > 0:
        return row

    token_usage = _parse_json_field(row.get("token_usage") or {})

    if not isinstance(token_usage, dict):
        token_usage = {}

    execution = execution_from_stage_run(row)
    has_token_usage = any(token_usage.values())
    has_llamaparse = row.get("stage_id") == "parse" and execution.get("page_count")

    if not has_token_usage and not has_llamaparse:
        return row

    return {**row, **backfill_fields_for_stage_run(row)}
