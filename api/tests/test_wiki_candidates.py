from app.intellex.wiki_candidates import (
    WikiCandidate,
    promote_candidates,
    resolve_prerequisites,
)


def _candidate(label: str, definition: str, **kwargs) -> WikiCandidate:
    return WikiCandidate(label=label, definition=definition, **kwargs)


def _existing_entry(
    slug: str,
    label: str,
    definition: str,
    *,
    entry_kind: str = "concept",
    importance: str = "supporting",
    aliases: list[str] | None = None,
    evidence: list[dict] | None = None,
) -> dict:
    return {
        "id": f"wiki-{slug}",
        "canonical_slug": slug,
        "preferred_label": label,
        "definition": definition,
        "entry_kind": entry_kind,
        "importance": importance,
        "aliases": aliases or [],
        "evidence": evidence or [],
        "status": "canonical",
    }


def test_new_candidate_inserts_canonical_row() -> None:
    inserts, updates, conflicted = promote_candidates(
        workspace_id="ws-1",
        candidates=[
            _candidate(
                "Enemy System",
                "The enemy as a system of interdependent parts.",
                entry_kind="concept",
                importance="essential",
                evidence=[{"source_id": "src-1", "segment_id": "seg-1", "page": 87}],
                origin={"kind": "manual", "batch_id": "batch-1"},
            ),
        ],
        existing_entries=[],
    )

    assert updates == []
    assert conflicted == []
    assert len(inserts) == 1
    row = inserts[0]
    assert row["canonical_slug"] == "enemy-system"
    assert row["status"] == "canonical"
    assert row["importance"] == "essential"
    assert row["evidence"][0]["segment_id"] == "seg-1"
    assert row["origin"]["kind"] == "manual"


def test_compatible_definition_merges_aliases_evidence_and_importance() -> None:
    existing = _existing_entry(
        "tempo",
        "Tempo",
        "Tempo is the rate of operations",
        importance="supporting",
        aliases=["operational tempo"],
        evidence=[{"source_id": "src-1", "segment_id": "seg-1", "page": 1}],
    )

    inserts, updates, conflicted = promote_candidates(
        workspace_id="ws-1",
        candidates=[
            _candidate(
                "Tempo",
                # Superset of the existing definition — compatible, not a conflict.
                "Tempo is the rate of operations relative to the enemy.",
                importance="essential",
                aliases=["ops tempo"],
                evidence=[{"source_id": "src-1", "segment_id": "seg-2", "page": 2}],
            ),
        ],
        existing_entries=[existing],
    )

    assert inserts == []
    assert conflicted == []
    update = updates[0]
    assert update["id"] == "wiki-tempo"
    assert "operational tempo" in update["aliases"]
    assert "ops tempo" in update["aliases"]
    assert update["importance"] == "essential"
    assert {record["segment_id"] for record in update["evidence"]} == {"seg-1", "seg-2"}


def test_conflict_without_override_is_reported_untouched() -> None:
    existing = _existing_entry("tempo", "Tempo", "Tempo is a musical term.")

    inserts, updates, conflicted = promote_candidates(
        workspace_id="ws-1",
        candidates=[_candidate("Tempo", "The rate of military operations.")],
        existing_entries=[existing],
    )

    assert inserts == []
    assert updates == []
    assert conflicted == [0]


def test_conflict_with_override_applies_candidate_definition() -> None:
    existing = _existing_entry("tempo", "Tempo", "Tempo is a musical term.")

    _, updates, conflicted = promote_candidates(
        workspace_id="ws-1",
        candidates=[_candidate("Tempo", "The rate of military operations.")],
        existing_entries=[existing],
        override_conflicts=True,
    )

    assert conflicted == []
    assert updates[0]["definition"] == "The rate of military operations."
    assert updates[0]["status"] == "canonical"


def test_insight_diverges_from_definitional_slug() -> None:
    existing = _existing_entry("tempo", "Tempo", "The rate of operations.")

    inserts, updates, _ = promote_candidates(
        workspace_id="ws-1",
        candidates=[
            _candidate(
                "Tempo",
                "Faster decision cycles beat stronger forces.",
                entry_kind="insight",
            ),
        ],
        existing_entries=[existing],
    )

    assert updates == []
    assert inserts[0]["canonical_slug"] == "tempo--insight"


def test_term_and_concept_share_a_slug() -> None:
    existing = _existing_entry(
        "tempo",
        "Tempo",
        "The rate of operations.",
        entry_kind="term",
    )

    inserts, updates, _ = promote_candidates(
        workspace_id="ws-1",
        candidates=[
            _candidate("Tempo", "The rate of operations.", entry_kind="concept"),
        ],
        existing_entries=[existing],
    )

    assert inserts == []
    # Kind upgrades to the richer concept.
    assert updates[0]["entry_kind"] == "concept"


def test_resolve_prerequisites_maps_labels_to_ids() -> None:
    wiki_rows = [
        _existing_entry("enemy-system", "Enemy System", "def"),
        _existing_entry("center-of-gravity", "Center of Gravity", "def"),
    ]
    candidates = [
        _candidate(
            "Center of Gravity",
            "def",
            prerequisite_labels=["Enemy System", "Nonexistent Label"],
        ),
    ]

    updates = resolve_prerequisites(candidates=candidates, wiki_rows=wiki_rows)

    assert updates == [
        {"id": "wiki-center-of-gravity", "prerequisites": ["wiki-enemy-system"]},
    ]
