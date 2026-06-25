from app.intellex.selection import (
    calibrate_importance,
    enforce_budget,
    ensure_objective_coverage,
    objective_concept_slugs,
    resolve_canonical_selection,
    selection_score,
)
from app.intellex.stages.concept_models import DeconstructedConcept, LearningObjective


def _concept(
    label: str,
    *,
    importance: str = "essential",
    confidence: float = 0.5,
    evidence: int = 1,
    objectives: int = 0,
) -> DeconstructedConcept:
    return DeconstructedConcept(
        term_label=label,
        definition=f"Definition of {label}.",
        importance=importance,
        confidence=confidence,
        evidence_segment_ids=[f"{label}-seg-{i}" for i in range(evidence)],
        objective_labels=[f"obj-{i}" for i in range(objectives)],
    )


def test_calibrate_collapses_importance_inflation() -> None:
    # Ten items all self-rated essential; calibration must enforce a spread.
    items = [
        _concept(f"c{i}", importance="essential", confidence=i / 10.0)
        for i in range(10)
    ]

    calibrate_importance(items, essential_fraction=0.2, supporting_fraction=0.4)

    counts = {"essential": 0, "supporting": 0, "contextual": 0}
    for item in items:
        counts[item.importance] += 1

    assert counts == {"essential": 2, "supporting": 4, "contextual": 4}


def test_calibrate_guarantees_at_least_one_essential() -> None:
    items = [
        _concept("a", importance="contextual"),
        _concept("b", importance="contextual"),
        _concept("c", importance="contextual"),
    ]

    calibrate_importance(items, essential_fraction=0.2, supporting_fraction=0.4)

    assert sum(1 for item in items if item.importance == "essential") == 1


def test_calibrate_ranks_by_evidence_and_objective_linkage() -> None:
    strong = _concept("strong", importance="supporting", evidence=3, objectives=2, confidence=0.5)
    weak = _concept("weak", importance="essential", evidence=0, objectives=0, confidence=0.5)

    # Despite "weak" self-rating essential, the better-grounded item outranks it.
    assert selection_score(strong) > selection_score(weak)

    calibrate_importance([strong, weak], essential_fraction=0.5, supporting_fraction=0.5)

    assert strong.importance == "essential"
    assert weak.importance == "supporting"


def test_calibrate_empty_is_noop() -> None:
    assert calibrate_importance([], essential_fraction=0.2, supporting_fraction=0.4) == []


def test_resolve_canonical_selection_no_budget_keeps_all() -> None:
    items = [_concept("a"), _concept("b"), _concept("c")]
    assert resolve_canonical_selection(items, budget=0, selected_labels=["a"]) == {0, 1, 2}


def test_resolve_canonical_selection_uses_curator_labels() -> None:
    items = [_concept("Alpha"), _concept("Beta"), _concept("Gamma")]
    selected = resolve_canonical_selection(items, budget=2, selected_labels=["alpha", "Gamma"])
    assert selected == {0, 2}


def test_resolve_canonical_selection_caps_over_budget_picks_by_score() -> None:
    items = [
        _concept("Alpha", evidence=3, objectives=2),  # highest score
        _concept("Beta", evidence=0),
        _concept("Gamma", evidence=1),
    ]
    # Curator over-selects; gate must trim to the single highest scorer.
    selected = resolve_canonical_selection(
        items, budget=1, selected_labels=["Alpha", "Beta", "Gamma"],
    )
    assert selected == {0}


def test_resolve_canonical_selection_falls_back_when_labels_invalid() -> None:
    items = [
        _concept("Alpha", evidence=3, objectives=2),
        _concept("Beta", evidence=0),
    ]
    selected = resolve_canonical_selection(items, budget=1, selected_labels=["Nonexistent"])
    assert selected == {0}  # top scorer


def test_enforce_budget_is_noop_within_budget() -> None:
    items = [_concept("a"), _concept("b")]
    assert enforce_budget({0, 1}, items, 3) == {0, 1}


def _objective(objective_id: str, *, concept_labels=None) -> LearningObjective:
    return LearningObjective(
        objective_id=objective_id,
        statement="Understand X",
        bloom_level="understand",
        concept_labels=concept_labels or [],
    )


def test_objective_concept_slugs_captures_linkage() -> None:
    items = [
        DeconstructedConcept(
            term_label="Tempo",
            definition="d",
            aliases=["Operational Tempo"],
            objective_labels=["obj-1"],
        ),
        DeconstructedConcept(term_label="Logistics", definition="d", objective_labels=["obj-2"]),
    ]

    mapping = objective_concept_slugs(items)

    assert mapping["obj-1"] == {"tempo", "operational-tempo"}
    assert mapping["obj-2"] == {"logistics"}


def test_ensure_objective_coverage_backfills_and_promotes() -> None:
    items = [
        _concept("Tempo", importance="supporting", evidence=3, objectives=1),
        _concept("Surprise", importance="contextual", evidence=1),
    ]
    objectives = [_objective("obj-1")]
    objective_slugs = {"obj-1": {"tempo", "surprise"}}

    ensure_objective_coverage(items, objectives, objective_slugs)

    # concept_labels backfilled from the linked concepts...
    assert objectives[0].concept_labels == ["Surprise", "Tempo"]
    # ...and the best-scoring linked concept is promoted to essential.
    assert items[0].importance == "essential"  # Tempo: more evidence + objective
    assert items[1].importance == "contextual"


def test_ensure_objective_coverage_leaves_satisfied_objectives() -> None:
    items = [_concept("Tempo", importance="essential", evidence=3)]
    objectives = [_objective("obj-1")]

    ensure_objective_coverage(items, objectives, {"obj-1": {"tempo"}})

    # Already has an essential; nothing forced to change importance.
    assert items[0].importance == "essential"
    assert objectives[0].concept_labels == ["Tempo"]
