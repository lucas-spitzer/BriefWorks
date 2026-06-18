from app.qngen.canonical_context import batch_concepts, build_source_concepts


def test_build_source_concepts_filters_by_source_evidence() -> None:
    concepts = build_source_concepts(
        wiki_entries=[
            {
                "id": "wiki-1",
                "status": "canonical",
                "preferred_label": "Combined Arms",
                "definition": "Integration of arms.",
                "aliases": [],
                "importance": "essential",
                "prerequisites": [],
                "evidence": [
                    {"source_id": "src-1", "segment_id": "seg-1"},
                    {"source_id": "src-2", "segment_id": "seg-9"},
                ],
            },
            {
                "id": "wiki-2",
                "status": "canonical",
                "preferred_label": "Other Source Term",
                "definition": "Not for this source.",
                "aliases": [],
                "importance": "essential",
                "prerequisites": [],
                "evidence": [{"source_id": "src-2", "segment_id": "seg-2"}],
            },
            {
                "id": "wiki-3",
                "status": "disputed",
                "preferred_label": "Disputed",
                "definition": "Should be excluded.",
                "aliases": [],
                "importance": "essential",
                "prerequisites": [],
                "evidence": [{"source_id": "src-1", "segment_id": "seg-3"}],
            },
        ],
        source_id="src-1",
        segments=[
            {"id": "seg-1", "kind": "paragraph", "text": "Combined arms text.", "locator": {"page": 1}},
        ],
    )

    assert len(concepts) == 1
    assert concepts[0].wiki_id == "wiki-1"
    assert concepts[0].evidence_segment_ids == ["seg-1"]
    assert concepts[0].evidence_segments[0]["text"] == "Combined arms text."


def test_build_source_concepts_sorts_by_importance() -> None:
    concepts = build_source_concepts(
        wiki_entries=[
            {
                "id": "wiki-supporting",
                "status": "canonical",
                "preferred_label": "Supporting",
                "definition": "Supporting concept.",
                "aliases": [],
                "importance": "supporting",
                "prerequisites": [],
                "evidence": [{"source_id": "src-1", "segment_id": "seg-1"}],
            },
            {
                "id": "wiki-essential",
                "status": "canonical",
                "preferred_label": "Essential",
                "definition": "Essential concept.",
                "aliases": [],
                "importance": "essential",
                "prerequisites": [],
                "evidence": [{"source_id": "src-1", "segment_id": "seg-2"}],
            },
        ],
        source_id="src-1",
        segments=[
            {"id": "seg-1", "kind": "paragraph", "text": "A", "locator": {}},
            {"id": "seg-2", "kind": "paragraph", "text": "B", "locator": {}},
        ],
    )

    assert [concept.wiki_id for concept in concepts] == ["wiki-essential", "wiki-supporting"]


def test_batch_concepts_splits_into_fixed_size_batches() -> None:
    concepts = build_source_concepts(
        wiki_entries=[
            {
                "id": f"wiki-{index}",
                "status": "canonical",
                "preferred_label": f"Term {index}",
                "definition": f"Definition {index}",
                "aliases": [],
                "importance": "supporting",
                "prerequisites": [],
                "evidence": [{"source_id": "src-1", "segment_id": f"seg-{index}"}],
            }
            for index in range(5)
        ],
        source_id="src-1",
        segments=[
            {"id": f"seg-{index}", "kind": "paragraph", "text": f"Text {index}", "locator": {}}
            for index in range(5)
        ],
    )

    batches = batch_concepts(concepts, batch_size=2)

    assert len(batches) == 3
    assert len(batches[0]) == 2
    assert len(batches[-1]) == 1
