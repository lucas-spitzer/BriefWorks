"""Wiki-entry selection signals and calibration (extraction redesign).

Today each extracted item self-declares its importance, which inflates toward
"essential" and defeats QnGen's importance-based filtering. This module ranks
candidates by a composite signal and re-buckets importance *comparatively*, so
the distribution is stable regardless of how generous the model was.
"""

from __future__ import annotations

from collections import defaultdict

from app.intellex.stages.concept_models import DeconstructedConcept, LearningObjective
from app.intellex.wiki_slug import normalize_slug

# The model's self-rated importance is kept only as a weak prior; evidence and
# objective linkage carry more weight because they are observable, not declared.
_IMPORTANCE_PRIOR = {"essential": 1.0, "supporting": 0.5, "contextual": 0.0}
_EVIDENCE_SATURATION = 3.0


def selection_score(item: DeconstructedConcept) -> float:
    """Composite 0–1 score used to rank a candidate against its peers.

    Weighted blend of evidence breadth (a proxy for recurrence/grounding),
    whether it serves a learning objective, extractor confidence, and the
    model's self-rated importance as a tiebreaking prior. Persisted on the wiki
    entry and shown to the curation gate.
    """
    evidence_score = min(len(item.evidence_segment_ids) / _EVIDENCE_SATURATION, 1.0)
    objective_score = 1.0 if item.objective_labels else 0.0
    confidence = max(0.0, min(item.confidence, 1.0))
    prior = _IMPORTANCE_PRIOR.get(item.importance, 0.5)

    return (
        0.35 * evidence_score
        + 0.25 * objective_score
        + 0.20 * confidence
        + 0.20 * prior
    )


def calibrate_importance(
    items: list[DeconstructedConcept],
    *,
    essential_fraction: float,
    supporting_fraction: float,
) -> list[DeconstructedConcept]:
    """Re-assign importance by document-wide comparative ranking.

    The top ``essential_fraction`` of candidates (by :func:`selection_signal`)
    become ``essential``, the next ``supporting_fraction`` become ``supporting``,
    and the remainder ``contextual``. At least one essential is guaranteed when
    any items exist, so a document never loses its top-tier entirely. Order is
    preserved; only ``importance`` is mutated.
    """
    if not items:
        return items

    total = len(items)
    ranked_indices = sorted(
        range(total),
        key=lambda index: selection_score(items[index]),
        reverse=True,
    )

    essential_cut = max(1, round(total * essential_fraction))
    supporting_cut = essential_cut + max(0, round(total * supporting_fraction))

    for rank, index in enumerate(ranked_indices):
        if rank < essential_cut:
            items[index].importance = "essential"
        elif rank < supporting_cut:
            items[index].importance = "supporting"
        else:
            items[index].importance = "contextual"

    return items


def objective_concept_slugs(
    items: list[DeconstructedConcept],
) -> dict[str, set[str]]:
    """Map each objective_id to the slugs of concepts that cite it.

    Captured *before* consolidation, where ``objective_labels`` is reliable, so
    coverage survives the LLM consolidation pass that may drop the field.
    """
    mapping: dict[str, set[str]] = defaultdict(set)
    for item in items:
        slugs = {normalize_slug(item.term_label)}
        slugs.update(normalize_slug(alias) for alias in item.aliases)
        for objective_id in item.objective_labels:
            mapping[objective_id].update(slugs)
    return dict(mapping)


def ensure_objective_coverage(
    items: list[DeconstructedConcept],
    objectives: list[LearningObjective],
    objective_slugs: dict[str, set[str]],
) -> list[DeconstructedConcept]:
    """Close the objective↔concept loop and guarantee essential coverage.

    For each objective: backfill its ``concept_labels`` from the linked concepts
    (the labels start empty and QnGen's blueprint matches on them), and if none
    of its concepts is ``essential``, promote the highest-scoring linked concept
    so every objective is backed by at least one essential entry.
    """
    slug_to_indices: dict[str, list[int]] = defaultdict(list)
    for index, item in enumerate(items):
        slug_to_indices[normalize_slug(item.term_label)].append(index)
        for alias in item.aliases:
            slug_to_indices[normalize_slug(alias)].append(index)

    for objective in objectives:
        linked = sorted(
            {
                index
                for slug in objective_slugs.get(objective.objective_id, set())
                for index in slug_to_indices.get(slug, [])
            },
        )
        if not linked:
            continue

        objective.concept_labels = sorted(
            {items[index].term_label for index in linked} | set(objective.concept_labels),
        )

        if not any(items[index].importance == "essential" for index in linked):
            best = max(linked, key=lambda index: selection_score(items[index]))
            items[best].importance = "essential"

    return items


def enforce_budget(
    indices: set[int],
    items: list[DeconstructedConcept],
    budget: int,
) -> set[int]:
    """Trim an index set to the top ``budget`` by score; no-op if within budget."""
    if budget <= 0 or len(indices) <= budget:
        return set(indices)
    ranked = sorted(indices, key=lambda index: selection_score(items[index]), reverse=True)
    return set(ranked[:budget])


def resolve_canonical_selection(
    items: list[DeconstructedConcept],
    *,
    budget: int,
    selected_labels: list[str],
) -> set[int]:
    """Decide which item indices become ``canonical``, given the curator's picks.

    Encapsulates the gate's deterministic guardrails so the LLM can never break
    them: no budget (or fewer items than budget) keeps everything; otherwise the
    curator's labels are resolved to indices, an empty/invalid selection falls
    back to the top scorers, and the result is always capped at ``budget``.
    """
    total = len(items)
    if budget <= 0 or total <= budget:
        return set(range(total))

    label_to_index: dict[str, int] = {}
    for index, item in enumerate(items):
        label_to_index.setdefault(item.term_label.strip().casefold(), index)

    chosen = {
        label_to_index[label.strip().casefold()]
        for label in selected_labels
        if label.strip().casefold() in label_to_index
    }
    if not chosen:
        chosen = set(range(total))

    return enforce_budget(chosen, items, budget)
