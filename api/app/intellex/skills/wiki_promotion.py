from __future__ import annotations

import re
from typing import Any

from app.intellex.skills.deconstructor_models import DeconstructedConcept
from app.intellex.wiki_slug import normalize_slug


def _normalize_definition(definition: str) -> str:
    return re.sub(r"\s+", " ", definition.strip().lower())


def _definitions_conflict(existing: str, proposed: str) -> bool:
    if _normalize_definition(existing) == _normalize_definition(proposed):
        return False

    shorter, longer = sorted([existing, proposed], key=len)
    return shorter not in longer


def build_evidence_records(
    *,
    source_id: str,
    concept: DeconstructedConcept,
    segment_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []

    for segment_id in concept.evidence_segment_ids:
        segment = segment_index.get(segment_id)

        if not segment:
            continue

        locator = segment.get("locator") or {}
        evidence.append(
            {
                "source_id": source_id,
                "segment_id": segment_id,
                "page": locator.get("page"),
            },
        )

    if evidence:
        return evidence

    return [
        {
            "source_id": source_id,
            "segment_id": None,
            "page": None,
        },
    ]


def promote_concepts_to_wiki(
    *,
    workspace_id: str,
    source_id: str,
    skill_run_id: str,
    skill_id: str,
    skill_version: str,
    concepts: list[DeconstructedConcept],
    segment_index: dict[str, dict[str, Any]],
    existing_entries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return wiki rows to insert, wiki rows to update, and dispute rows."""
    entries_by_slug = {
        str(entry["canonical_slug"]): entry
        for entry in existing_entries
    }
    inserts: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    disputes: list[dict[str, Any]] = []

    for output_index, concept in enumerate(concepts):
        slug = normalize_slug(concept.term_label)
        evidence = build_evidence_records(
            source_id=source_id,
            concept=concept,
            segment_index=segment_index,
        )
        origin = {
            "skill_run_id": skill_run_id,
            "output_index": output_index,
            "skill_id": skill_id,
            "skill_version": skill_version,
        }
        existing = entries_by_slug.get(slug)

        if not existing:
            row = {
                "workspace_id": workspace_id,
                "preferred_label": concept.term_label,
                "canonical_slug": slug,
                "definition": concept.definition,
                "pronunciation": concept.pronunciation,
                "aliases": concept.aliases,
                "prerequisites": [],
                "importance": concept.importance,
                "status": "canonical",
                "evidence": evidence,
                "origin": origin,
            }
            inserts.append(row)
            entries_by_slug[slug] = row
            continue

        if _definitions_conflict(str(existing.get("definition") or ""), concept.definition):
            disputes.append(
                {
                    "workspace_id": workspace_id,
                    "wiki_entry_id": existing.get("id"),
                    "term_label": concept.term_label,
                    "existing_definition": existing.get("definition"),
                    "proposed_definition": concept.definition,
                    "skill_run_id": skill_run_id,
                    "source_id": source_id,
                    "status": "open",
                },
            )
            updates.append(
                {
                    "id": existing["id"],
                    "status": "disputed",
                    "evidence": _merge_evidence(existing.get("evidence") or [], evidence),
                },
            )
            continue

        merged_aliases = sorted(
            {
                *(existing.get("aliases") or []),
                *concept.aliases,
                concept.term_label,
            },
        )
        updates.append(
            {
                "id": existing["id"],
                "definition": existing.get("definition") or concept.definition,
                "pronunciation": existing.get("pronunciation") or concept.pronunciation,
                "aliases": merged_aliases,
                "importance": _pick_importance(
                    str(existing.get("importance") or "supporting"),
                    concept.importance,
                ),
                "evidence": _merge_evidence(existing.get("evidence") or [], evidence),
                "origin": origin,
            },
        )

    return inserts, updates, disputes


def resolve_prerequisites(
    *,
    concepts: list[DeconstructedConcept],
    wiki_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    label_to_id: dict[str, str] = {}

    for row in wiki_rows:
        label_to_id[normalize_slug(str(row["preferred_label"]))] = str(row["id"])

        for alias in row.get("aliases") or []:
            label_to_id[normalize_slug(str(alias))] = str(row["id"])

    updates: list[dict[str, Any]] = []

    for row in wiki_rows:
        slug = str(row["canonical_slug"])
        matching_concepts = [
            concept
            for concept in concepts
            if normalize_slug(concept.term_label) == slug
        ]

        if not matching_concepts:
            continue

        prerequisite_ids: list[str] = []

        for label in matching_concepts[0].prerequisite_labels:
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


def _merge_evidence(
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


def _pick_importance(existing: str, proposed: str) -> str:
    priority = {"essential": 3, "supporting": 2, "contextual": 1}
    return proposed if priority.get(proposed, 0) > priority.get(existing, 0) else existing
