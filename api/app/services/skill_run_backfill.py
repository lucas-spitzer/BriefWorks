from __future__ import annotations

import json
from typing import Any

from app.services.skill_run_billing import (
    skill_run_completion_fields,
    tts_call_from_manifest,
)


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    return value


def _tts_calls_from_artifact_manifests(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    for manifest in manifests:
        if not isinstance(manifest, dict):
            continue

        call = tts_call_from_manifest(manifest)

        if call is not None:
            calls.append(call)

    return calls


def execution_from_skill_run(
    row: dict[str, Any],
    *,
    artifact_manifests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Rebuild billing execution metadata from a persisted skill_runs row."""

    token_usage = _parse_json_field(row.get("token_usage") or {})

    if not isinstance(token_usage, dict):
        token_usage = {}

    execution: dict[str, Any] = {
        "model": row.get("model"),
        "token_usage": token_usage,
    }

    if row.get("skill_id") == "source-research":
        output = _parse_json_field(row.get("output") or {})

        if isinstance(output, dict):
            web_sources = output.get("web_sources")

            if isinstance(web_sources, list) and web_sources:
                execution["web_search_count"] = 1

    execution["artifact_manifests"] = artifact_manifests or []
    return execution


def backfill_fields_for_skill_run(
    row: dict[str, Any],
    *,
    artifact_manifests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    execution = execution_from_skill_run(row, artifact_manifests=artifact_manifests)
    extra_calls = _tts_calls_from_artifact_manifests(execution.pop("artifact_manifests", []))
    return skill_run_completion_fields(execution, extra_calls=extra_calls or None)


def enrich_skill_run_row(row: dict[str, Any]) -> dict[str, Any]:
    """Fill in billing fields on read when older runs predate cost tracking."""

    if float(row.get("cost_usd") or 0) > 0:
        return row

    token_usage = _parse_json_field(row.get("token_usage") or {})

    if not isinstance(token_usage, dict) or not any(token_usage.values()):
        return row

    return {**row, **backfill_fields_for_skill_run(row)}
