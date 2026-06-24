from __future__ import annotations

import json
from typing import Any

from app.config import get_settings

_DEFAULT_MAX_CHARS = 80_000


def _segment_payload(segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "segment_id": segment["id"],
        "kind": segment.get("kind"),
        "text": segment.get("text"),
        "page": (segment.get("locator") or {}).get("page"),
    }


def _extract_budget(max_chars: int | None = None) -> int:
    if max_chars is not None:
        return max_chars

    configured = get_settings().intellex.extract_chapter_max_chars
    return configured if configured is not None else _DEFAULT_MAX_CHARS


def batch_chapter_segments_for_llm(
    segments: list[dict[str, Any]],
    *,
    max_chars: int | None = None,
) -> list[tuple[str, int]]:
    """Format chapter segments into one or more LLM payloads, each under max_chars."""

    budget = _extract_budget(max_chars)
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0

    for segment in segments:
        segment_payload = _segment_payload(segment)
        segment_chars = len(json.dumps(segment_payload))

        if segment_chars > budget:
            raise RuntimeError(
                f"Segment exceeds extract budget ({segment_chars} chars > {budget} limit). "
                "Split the segment or raise EXTRACT_CHAPTER_MAX_CHARS.",
            )

        if current and current_chars + segment_chars > budget:
            batches.append(current)
            current = []
            current_chars = 0

        current.append(segment_payload)
        current_chars += segment_chars

    if current:
        batches.append(current)

    return [
        (json.dumps(batch, indent=2), sum(len(json.dumps(item)) for item in batch))
        for batch in batches
    ]


def format_chapter_segments_for_llm(
    segments: list[dict[str, Any]],
    *,
    max_chars: int | None = None,
) -> tuple[str, int]:
    """Format chapter segments for a single LLM call. Raises if over budget."""

    batches = batch_chapter_segments_for_llm(segments, max_chars=max_chars)

    if len(batches) != 1:
        total_chars = sum(char_count for _, char_count in batches)
        budget = _extract_budget(max_chars)
        raise RuntimeError(
            f"Chapter exceeds extract budget ({total_chars} chars > {budget} limit). "
            "Split the chapter or raise EXTRACT_CHAPTER_MAX_CHARS.",
        )

    return batches[0]
