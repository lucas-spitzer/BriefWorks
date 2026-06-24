from app.qngen.canonical_context import ConceptCard, build_chapter_blueprint


def _concept(wiki_id: str, label: str, segment_ids: list[str], aliases=None) -> ConceptCard:
    return ConceptCard(
        wiki_id=wiki_id,
        preferred_label=label,
        definition=f"Definition for {label}",
        aliases=aliases or [],
        importance="essential",
        evidence_segment_ids=segment_ids,
        evidence_segments=[
            {"segment_id": sid, "kind": "paragraph", "text": "t", "page": 1}
            for sid in segment_ids
        ],
    )


def _chapters() -> list[dict]:
    return [
        {
            "chapter_id": "ch-2",
            "chapter_title": "Maneuver",
            "sequence_index": 2,
            "segment_ids": ["seg-3"],
            "objectives": [
                {
                    "objective_id": "obj-2",
                    "statement": "Explain tempo",
                    "bloom_level": "understand",
                    "concept_labels": ["Tempo"],
                },
            ],
        },
        {
            "chapter_id": "ch-1",
            "chapter_title": "Foundations",
            "sequence_index": 1,
            "segment_ids": ["seg-1", "seg-2"],
            "objectives": [
                {
                    "objective_id": "obj-1",
                    "statement": "Define war",
                    "concept_labels": ["War"],
                },
            ],
        },
    ]


def test_blueprint_groups_concepts_by_segment_overlap_and_orders_chapters() -> None:
    concepts = [
        _concept("wiki-war", "War", ["seg-1"]),
        _concept("wiki-tempo", "Tempo", ["seg-3"]),
    ]

    blueprint = build_chapter_blueprint(_chapters(), concepts)

    # Ordered by sequence_index.
    assert [chapter.chapter_id for chapter in blueprint] == ["ch-1", "ch-2"]

    foundations, maneuver = blueprint
    assert [c.wiki_id for c in foundations.concepts] == ["wiki-war"]
    assert [c.wiki_id for c in maneuver.concepts] == ["wiki-tempo"]


def test_blueprint_carries_objective_metadata_and_labels() -> None:
    concepts = [
        _concept("wiki-tempo", "Tempo", ["seg-3"]),
    ]

    blueprint = build_chapter_blueprint(_chapters(), concepts)
    maneuver = next(chapter for chapter in blueprint if chapter.chapter_id == "ch-2")

    assert len(maneuver.objectives) == 1
    objective = maneuver.objectives[0]
    assert objective.objective_id == "obj-2"
    assert objective.statement == "Explain tempo"
    assert objective.concept_labels == ["Tempo"]


def test_blueprint_empty_when_no_chapter_structure() -> None:
    concepts = [_concept("wiki-war", "War", ["seg-1"])]
    assert build_chapter_blueprint([], concepts) == []
