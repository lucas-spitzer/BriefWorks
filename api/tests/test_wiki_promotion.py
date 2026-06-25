from app.intellex.stages.concept_models import DeconstructedConcept
from app.intellex.stages.wiki_promotion import promote_concepts_to_wiki, resolve_prerequisites
from app.intellex.wiki_slug import normalize_slug


def test_normalize_slug() -> None:
    assert normalize_slug("METT-T") == "mett-t"
    assert normalize_slug("Rules of Engagement (ROE)") == "rules-of-engagement-roe"


def test_promote_concepts_creates_insert_for_new_term() -> None:
    concept = DeconstructedConcept(
        term_label="METT-T",
        definition="Mission, Enemy, Terrain and weather, Troops and support available, and Time available.",
        importance="essential",
        evidence_segment_ids=["seg-1"],
        confidence=0.95,
    )

    inserts, updates, disputes = promote_concepts_to_wiki(
        workspace_id="ws-1",
        source_id="src-1",
        stage_run_id="run-1",
        stage_id="deconstruct-document",
        stage_version="1.0",
        concepts=[concept],
        segment_index={
            "seg-1": {
                "id": "seg-1",
                "locator": {"page": 4},
            },
        },
        existing_entries=[],
    )

    assert len(inserts) == 1
    assert inserts[0]["canonical_slug"] == "mett-t"
    assert inserts[0]["entry_kind"] == "concept"
    assert inserts[0]["status"] == "canonical"
    assert updates == []
    assert disputes == []


def test_promote_merges_term_into_existing_concept_entry() -> None:
    # A term whose label matches an existing concept entry must update that
    # entry (not create a `tempo--term` duplicate), keeping the richer kind.
    concept = DeconstructedConcept(
        term_label="Tempo",
        definition="Speed over time.",
        entry_kind="term",
        importance="essential",
        evidence_segment_ids=["seg-1"],
    )

    inserts, updates, disputes = promote_concepts_to_wiki(
        workspace_id="ws-1",
        source_id="src-2",
        stage_run_id="run-2",
        stage_id="extract-chapter-knowledge",
        stage_version="2.0",
        concepts=[concept],
        segment_index={"seg-1": {"id": "seg-1", "locator": {"page": 1}}},
        existing_entries=[
            {
                "id": "wiki-tempo",
                "canonical_slug": "tempo",
                "preferred_label": "Tempo",
                "definition": "Speed over time.",
                "entry_kind": "concept",
                "aliases": [],
                "importance": "supporting",
                "evidence": [],
            },
        ],
    )

    assert inserts == []
    assert disputes == []
    assert len(updates) == 1
    assert updates[0]["id"] == "wiki-tempo"
    assert updates[0]["entry_kind"] == "concept"  # richer kind retained


def test_promote_keeps_insight_separate_from_concept() -> None:
    insight = DeconstructedConcept(
        term_label="Tempo",
        definition="Sustaining a faster tempo collapses enemy decision-making.",
        entry_kind="insight",
        importance="essential",
        evidence_segment_ids=["seg-1"],
    )

    inserts, updates, _disputes = promote_concepts_to_wiki(
        workspace_id="ws-1",
        source_id="src-2",
        stage_run_id="run-2",
        stage_id="extract-chapter-knowledge",
        stage_version="2.0",
        concepts=[insight],
        segment_index={"seg-1": {"id": "seg-1", "locator": {"page": 1}}},
        existing_entries=[
            {
                "id": "wiki-tempo",
                "canonical_slug": "tempo",
                "preferred_label": "Tempo",
                "definition": "Speed over time.",
                "entry_kind": "concept",
                "aliases": [],
                "evidence": [],
            },
        ],
    )

    assert updates == []
    assert len(inserts) == 1
    assert inserts[0]["canonical_slug"] == "tempo--insight"


def test_promote_concepts_logs_dispute_on_conflicting_definition() -> None:
    concept = DeconstructedConcept(
        term_label="ROE",
        definition="A completely different definition that should not merge.",
        importance="essential",
        evidence_segment_ids=[],
        confidence=0.9,
    )

    inserts, updates, disputes = promote_concepts_to_wiki(
        workspace_id="ws-1",
        source_id="src-1",
        stage_run_id="run-1",
        stage_id="deconstruct-document",
        stage_version="1.0",
        concepts=[concept],
        segment_index={},
        existing_entries=[
            {
                "id": "wiki-1",
                "canonical_slug": "roe",
                "preferred_label": "ROE",
                "definition": "Rules of Engagement govern the use of force.",
                "aliases": [],
                "evidence": [],
            },
        ],
    )

    assert inserts == []
    assert len(disputes) == 1
    assert updates[0]["status"] == "disputed"


def test_resolve_prerequisites_links_labels_to_wiki_ids() -> None:
    concepts = [
        DeconstructedConcept(
            term_label="METT-T",
            definition="Mission analysis framework.",
            prerequisite_labels=["mission analysis"],
            evidence_segment_ids=[],
            confidence=0.9,
        ),
    ]
    wiki_rows = [
        {
            "id": "wiki-1",
            "canonical_slug": "mett-t",
            "preferred_label": "METT-T",
            "aliases": [],
        },
        {
            "id": "wiki-2",
            "canonical_slug": "mission-analysis",
            "preferred_label": "mission analysis",
            "aliases": [],
        },
    ]

    updates = resolve_prerequisites(concepts=concepts, wiki_rows=wiki_rows)

    assert updates == [{"id": "wiki-1", "prerequisites": ["wiki-2"]}]
