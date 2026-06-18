from __future__ import annotations

import json
import os
from typing import Any

_DEFAULT_MAX_CHARS = 80_000


def format_chapter_segments_for_llm(
    segments: list[dict[str, Any]],
    *,
    max_chars: int | None = None,
) -> tuple[str, int]:
    """Format chapter segments for a single LLM call. Raises if over budget."""

    budget = max_chars or int(os.getenv("EXTRACT_CHAPTER_MAX_CHARS", str(_DEFAULT_MAX_CHARS)))
    payload: list[dict[str, Any]] = []
    total_chars = 0

    for segment in segments:
        segment_payload = {
            "segment_id": segment["id"],
            "kind": segment.get("kind"),
            "text": segment.get("text"),
            "page": (segment.get("locator") or {}).get("page"),
        }
        encoded = json.dumps(segment_payload)
        total_chars += len(encoded)

        if total_chars > budget:
            raise RuntimeError(
                f"Chapter exceeds extract budget ({total_chars} chars > {budget} limit). "
                "Split the chapter or raise EXTRACT_CHAPTER_MAX_CHARS.",
            )

        payload.append(segment_payload)

    return json.dumps(payload, indent=2), total_chars
