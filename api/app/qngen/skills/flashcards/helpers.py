# Flashcard skill helpers — deterministic post-processing hooks.

from __future__ import annotations

from typing import Any


def prefer_term_definition(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse duplicate flashcards down to one card per concept and per term.

    Two layers of dedup:

    1. By citing ``wiki_id`` — at most one card per canonical concept.
    2. By case-folded term front — collapses near-duplicate ``term_definition``
       cards that escaped the wiki dedup because canonicalization produced two
       entries differing only in casing (e.g. ``Enemy system`` vs
       ``enemy system``).

    Within a collision the best-grounded ``term_definition`` card wins: cards are
    ordered so ``term_definition`` comes first, then by citation count, then by
    definition length.
    """
    seen_wiki: set[str] = set()
    seen_front: set[str] = set()
    result: list[dict[str, Any]] = []

    for item in sorted(items, key=_dedup_rank):
        wiki_ids = item.get("wiki_ids_cited") or []
        primary = next(iter(wiki_ids), None)
        if primary and primary in seen_wiki:
            continue

        if item.get("subtype") == "term_definition":
            front_key = (item.get("front") or "").strip().casefold()
            if front_key and front_key in seen_front:
                continue
            if front_key:
                seen_front.add(front_key)

        if primary:
            seen_wiki.add(primary)
        result.append(item)

    return result


def _dedup_rank(item: dict[str, Any]) -> tuple[int, int, int]:
    is_term_definition = 0 if item.get("subtype") == "term_definition" else 1
    citation_count = len(item.get("source_chunk_ids") or [])
    definition_length = len(item.get("back") or "")
    return (is_term_definition, -citation_count, -definition_length)
