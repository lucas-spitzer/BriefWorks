"""Producer-neutral wiki promotion.

A ``WikiCandidate`` is a fully-specified proposed wiki entry, independent of
where it came from (today: the manual authoring flow; formerly: extraction).
``promote_candidates`` turns a candidate set into insert/update payloads for
``wiki_entries`` while enforcing the workspace's slug-uniqueness and merge
semantics: aliases union, evidence records dedup on ``(source_id, segment_id)``,
importance keeps the higher tier, and a term/concept pair for the same subject
collapses into one entry while insights diverge to a kind-suffixed slug.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.intellex.wiki_slug import normalize_slug

Importance = Literal["essential", "supporting", "contextual"]
EntryKind = Literal["term", "concept", "insight"]

ENTRY_KIND_PRIORITY = {"concept": 2, "term": 1, "insight": 0}


def merge_group(entry_kind: str) -> str:
    """Group key for dedup: ``term`` and ``concept`` collapse together.

    A subject captured as both a term and a concept describes the same
    vocabulary item and must not become two wiki entries. Insights are headline
    takeaways with distinct labels, so they stay in their own group.
    """
    return "definitional" if entry_kind in {"term", "concept"} else entry_kind


def pick_entry_kind(existing: str, proposed: str) -> str:
    """Return the richer of two entry kinds (concept > term > insight)."""
    if ENTRY_KIND_PRIORITY.get(proposed, 0) > ENTRY_KIND_PRIORITY.get(existing, 0):
        return proposed
    return existing


def pick_importance(existing: str, proposed: str) -> str:
    priority = {"essential": 3, "supporting": 2, "contextual": 1}
    return proposed if priority.get(proposed, 0) > priority.get(existing, 0) else existing


class WikiCandidate(BaseModel):
    label: str
    definition: str
    entry_kind: EntryKind = "concept"
    aliases: list[str] = Field(default_factory=list)
    prerequisite_labels: list[str] = Field(default_factory=list)
    pronunciation: str | None = None
    importance: Importance = "supporting"
    # Evidence records already in wiki_entries shape:
    # {"source_id": …, "segment_id": …, "page": …, "quote"?: …}
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    origin: dict[str, Any] = Field(default_factory=dict)


def candidate_slug(
    candidate: WikiCandidate,
    entries_by_slug: dict[str, dict[str, Any]],
) -> str:
    base = normalize_slug(candidate.label)
    existing = entries_by_slug.get(base)

    # Only diverge to a kind-suffixed slug when the existing entry is in a
    # different merge group (e.g. an insight vs a term/concept).
    if existing and merge_group(str(existing.get("entry_kind") or "concept")) != merge_group(
        candidate.entry_kind
    ):
        return f"{base}--{candidate.entry_kind}"

    return base


def _normalize_definition(definition: str) -> str:
    return re.sub(r"\s+", " ", definition.strip().lower())


def definitions_conflict(existing: str, proposed: str) -> bool:
    if _normalize_definition(existing) == _normalize_definition(proposed):
        return False

    shorter, longer = sorted([existing, proposed], key=len)
    return shorter not in longer


def merge_evidence(
    existing: list[dict[str, Any]],
    new_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = {
        (item.get("source_id"), item.get("segment_id"))
        for item in existing
    }
    merged = list(existing)

    for item in new_items:
        key = (item.get("source_id"), item.get("segment_id"))

        if key in seen:
            continue

        merged.append(item)
        seen.add(key)

    return merged


def promote_candidates(
    *,
    workspace_id: str,
    candidates: list[WikiCandidate],
    existing_entries: list[dict[str, Any]],
    override_conflicts: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[int]]:
    """Return wiki rows to insert, wiki rows to update, and conflicted indexes.

    ``override_conflicts=False`` leaves conflicting candidates untouched and
    reports their indexes so the caller can surface them; ``True`` applies the
    candidate's definition over the existing one (the reviewed human choice
    wins — the manual flow's dispute resolution).
    """
    entries_by_slug = {
        str(entry["canonical_slug"]): entry
        for entry in existing_entries
    }
    inserts: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    conflicted: list[int] = []

    for index, candidate in enumerate(candidates):
        slug = candidate_slug(candidate, entries_by_slug)
        existing = entries_by_slug.get(slug)

        if not existing:
            row = {
                "workspace_id": workspace_id,
                "preferred_label": candidate.label,
                "canonical_slug": slug,
                "definition": candidate.definition,
                "pronunciation": candidate.pronunciation,
                "aliases": candidate.aliases,
                "prerequisites": [],
                "importance": candidate.importance,
                "entry_kind": candidate.entry_kind,
                "status": "canonical",
                "evidence": candidate.evidence,
                "origin": candidate.origin,
            }
            inserts.append(row)
            entries_by_slug[slug] = row
            continue

        conflict = definitions_conflict(
            str(existing.get("definition") or ""),
            candidate.definition,
        )

        if conflict and not override_conflicts:
            conflicted.append(index)
            continue

        merged_aliases = sorted(
            {
                *(existing.get("aliases") or []),
                *candidate.aliases,
                candidate.label,
            }
            - {str(existing.get("preferred_label") or "")},
        )
        updates.append(
            {
                "id": existing["id"],
                "definition": (
                    candidate.definition
                    if conflict
                    else existing.get("definition") or candidate.definition
                ),
                "pronunciation": existing.get("pronunciation") or candidate.pronunciation,
                "aliases": merged_aliases,
                "importance": pick_importance(
                    str(existing.get("importance") or "supporting"),
                    candidate.importance,
                ),
                "entry_kind": pick_entry_kind(
                    str(existing.get("entry_kind") or "concept"),
                    candidate.entry_kind,
                ),
                "status": "canonical",
                "evidence": merge_evidence(existing.get("evidence") or [], candidate.evidence),
                "origin": candidate.origin,
            },
        )

    return inserts, updates, conflicted


def resolve_prerequisites(
    *,
    candidates: list[WikiCandidate],
    wiki_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map candidate ``prerequisite_labels`` to wiki ids across the workspace.

    Labels that match nothing are dropped silently — a prerequisite the author
    named but never curated is not an error.
    """
    label_to_id: dict[str, str] = {}

    for row in wiki_rows:
        label_to_id[normalize_slug(str(row["preferred_label"]))] = str(row["id"])

        for alias in row.get("aliases") or []:
            label_to_id[normalize_slug(str(alias))] = str(row["id"])

    updates: list[dict[str, Any]] = []

    for row in wiki_rows:
        slug = str(row["canonical_slug"])
        matching = [
            candidate
            for candidate in candidates
            if normalize_slug(candidate.label) == slug
        ]

        if not matching:
            continue

        prerequisite_ids: list[str] = []

        for label in matching[0].prerequisite_labels:
            wiki_id = label_to_id.get(normalize_slug(label))

            if wiki_id and wiki_id != row.get("id"):
                prerequisite_ids.append(wiki_id)

        if prerequisite_ids:
            updates.append(
                {
                    "id": row["id"],
                    "prerequisites": sorted(set(prerequisite_ids)),
                },
            )

    return updates
