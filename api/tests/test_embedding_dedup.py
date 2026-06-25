from app.intellex.stages.concept_models import DeconstructedConcept
from app.intellex.stages.extract_chapter_knowledge import (
    _cosine_similarity,
    deduplicate_by_embedding,
)


def _concept(label: str, *, entry_kind: str = "concept", definition: str = "d") -> DeconstructedConcept:
    return DeconstructedConcept(
        term_label=label,
        definition=definition,
        entry_kind=entry_kind,
        evidence_segment_ids=[f"{label}-seg"],
    )


def test_cosine_similarity() -> None:
    assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0  # zero-norm guard


def test_dedup_merges_near_duplicate_vectors() -> None:
    items = [
        _concept("Maneuver warfare"),
        _concept("Maneuverist approach"),  # near-duplicate by vector
        _concept("Logistics"),  # unrelated
    ]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.99, 0.01, 0.0],  # cosine ~1.0 with the first
        [0.0, 0.0, 1.0],
    ]

    result = deduplicate_by_embedding(items, embeddings, threshold=0.9)

    assert len(result) == 2
    survivor = result[0]
    assert survivor.term_label == "Maneuver warfare"
    # Merged item's label is folded into aliases and evidence is unioned.
    assert "Maneuverist approach" in survivor.aliases
    assert set(survivor.evidence_segment_ids) == {"Maneuver warfare-seg", "Maneuverist approach-seg"}


def test_dedup_does_not_merge_across_entry_kind_groups() -> None:
    items = [
        _concept("Tempo", entry_kind="concept"),
        _concept("Tempo", entry_kind="insight"),
    ]
    embeddings = [[1.0, 0.0], [1.0, 0.0]]  # identical vectors

    result = deduplicate_by_embedding(items, embeddings, threshold=0.9)

    # Different merge groups (definitional vs insight) stay separate.
    assert len(result) == 2


def test_dedup_noop_when_below_threshold() -> None:
    items = [_concept("A"), _concept("B")]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]

    result = deduplicate_by_embedding(items, embeddings, threshold=0.9)

    assert len(result) == 2


def test_dedup_noop_on_length_mismatch() -> None:
    items = [_concept("A"), _concept("B")]
    assert deduplicate_by_embedding(items, [[1.0]], threshold=0.9) is items
