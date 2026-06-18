from app.qngen.canonical_context import ConceptCard
from app.qngen.validators import validate_assessment_items


def _concept() -> ConceptCard:
    return ConceptCard(
        wiki_id="wiki-1",
        preferred_label="Combined Arms",
        definition="Integration of arms.",
        aliases=["combined arms warfare"],
        importance="essential",
        evidence_segment_ids=["seg-1"],
        evidence_segments=[
            {"segment_id": "seg-1", "kind": "paragraph", "text": "Combined arms text.", "page": 1},
        ],
    )


def test_validate_assessment_items_drops_invalid_citations() -> None:
    items = [
        {
            "item_id": "item-1",
            "type": "flashcard",
            "subtype": "term_definition",
            "difficulty": "easy",
            "front": "What is Combined Arms?",
            "back": "Integration of arms.",
            "wiki_ids_cited": ["wiki-unknown"],
            "source_chunk_ids": ["seg-1"],
        },
        {
            "item_id": "item-2",
            "type": "quiz",
            "subtype": "multiple_choice",
            "difficulty": "medium",
            "question": "What is Combined Arms?",
            "choices": ["A", "B"],
            "correct_answer": "A",
            "wiki_ids_cited": ["wiki-1"],
            "source_chunk_ids": ["seg-1"],
        },
    ]

    validated, report = validate_assessment_items(
        items=items,
        concepts=[_concept()],
        segment_ids={"seg-1"},
        wiki_ids={"wiki-1"},
    )

    assert len(validated) == 1
    assert validated[0]["type"] == "quiz"
    assert report["dropped_invalid_citations"] == 1


def test_validate_assessment_items_drops_invalid_quiz_answer() -> None:
    items = [
        {
            "item_id": "item-1",
            "type": "quiz",
            "subtype": "multiple_choice",
            "difficulty": "medium",
            "question": "What is Combined Arms?",
            "choices": ["Integration of arms.", "Random answer"],
            "correct_answer": "Not in choices",
            "wiki_ids_cited": ["wiki-1"],
            "source_chunk_ids": ["seg-1"],
        },
    ]

    validated, report = validate_assessment_items(
        items=items,
        concepts=[_concept()],
        segment_ids={"seg-1"},
        wiki_ids={"wiki-1"},
    )

    assert validated == []
    assert report["dropped_invalid_quiz_answer"] == 1
