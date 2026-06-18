from __future__ import annotations

import json
from typing import Any


def format_segments_for_llm(segments: list[dict[str, Any]], *, max_chars: int = 24_000) -> str:
    compact_segments: list[dict[str, Any]] = []
    total_chars = 0

    for segment in segments:
        payload = {
            "segment_id": segment["id"],
            "kind": segment.get("kind"),
            "text": segment.get("text"),
            "page": (segment.get("locator") or {}).get("page"),
        }
        encoded = json.dumps(payload)

        if total_chars + len(encoded) > max_chars:
            break

        compact_segments.append(payload)
        total_chars += len(encoded)

    return json.dumps(compact_segments, indent=2)


def split_segments_into_batches(
    segments: list[dict[str, Any]],
    *,
    batch_size: int = 40,
) -> list[list[dict[str, Any]]]:
    if not segments:
        return []

    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []

    for segment in segments:
        # Prefer to start a new batch at a heading so a section stays together,
        # but only once the current batch is already full enough. Splitting on
        # every heading produces one LLM call per heading in heading-dense
        # documents, which is needlessly slow and expensive.
        is_heading = segment.get("kind") == "heading"

        if is_heading and len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []

        current_batch.append(segment)

        if len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []

    if current_batch:
        batches.append(current_batch)

    return batches
