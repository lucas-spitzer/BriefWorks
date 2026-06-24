# Quiz skill helpers — deterministic post-processing hooks.

from __future__ import annotations

from typing import Any

from app.qngen.skills.shared.item_mapping import normalize_question_type


def normalize_quiz_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for item in items:
        row = dict(item)
        subtype = row.get("subtype") or "multiple_choice"
        row["subtype"] = subtype
        row["question_type"] = normalize_question_type(subtype)
        normalized.append(row)

    return normalized
