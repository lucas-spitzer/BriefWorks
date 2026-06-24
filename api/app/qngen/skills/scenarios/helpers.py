# Scenario skill helpers — deterministic post-processing hooks.

from __future__ import annotations

from typing import Any


def filter_essential_only(
    items: list[dict[str, Any]],
    *,
    essential_wiki_ids: set[str],
) -> list[dict[str, Any]]:
    """Scenarios are generated only for essential concepts."""
    return [
        item
        for item in items
        if essential_wiki_ids.intersection(item.get("wiki_ids_cited") or [])
    ]
