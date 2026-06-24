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


def _quiz_item(*, subtype: str, choices: list[str], correct_answer: str) -> dict:
    return {
        "item_id": "item-1",
        "type": "quiz",
        "subtype": subtype,
        "difficulty": "medium",
        "question": "What is Combined Arms?",
        "choices": choices,
        "correct_answer": correct_answer,
        "wiki_ids_cited": ["wiki-1"],
        "source_chunk_ids": ["seg-1"],
    }


def test_true_false_answer_is_validated_and_repaired() -> None:
    # Plain ``true_false`` previously bypassed the answer check entirely. A
    # leading-choice answer should now be coerced back to the verbatim choice.
    items = [
        _quiz_item(
            subtype="true_false",
            choices=["True", "False"],
            correct_answer="False - chance cannot be controlled.",
        ),
    ]

    validated, report = validate_assessment_items(
        items=items,
        concepts=[_concept()],
        segment_ids={"seg-1"},
        wiki_ids={"wiki-1"},
    )

    assert len(validated) == 1
    assert validated[0]["correct_answer"] == "False"
    assert report["repaired_quiz_answer"] == 1
    assert report["dropped_invalid_quiz_answer"] == 0


def test_option_label_answer_is_repaired() -> None:
    items = [
        _quiz_item(
            subtype="multiple_choice",
            choices=["Integration of arms.", "Random answer"],
            correct_answer="A) Integration of arms.",
        ),
    ]

    validated, report = validate_assessment_items(
        items=items,
        concepts=[_concept()],
        segment_ids={"seg-1"},
        wiki_ids={"wiki-1"},
    )

    assert len(validated) == 1
    assert validated[0]["correct_answer"] == "Integration of arms."
    assert report["repaired_quiz_answer"] == 1


def test_non_boundary_prefix_is_not_coerced() -> None:
    # "Falsehood" starts with "False" but is a different word — must not be
    # silently mapped onto the "False" choice.
    items = [
        _quiz_item(
            subtype="true_false",
            choices=["True", "False"],
            correct_answer="Falsehood is the wrong frame here",
        ),
    ]

    validated, report = validate_assessment_items(
        items=items,
        concepts=[_concept()],
        segment_ids={"seg-1"},
        wiki_ids={"wiki-1"},
    )

    assert validated == []
    assert report["dropped_invalid_quiz_answer"] == 1


def test_bare_letter_answer_is_repaired() -> None:
    items = [
        _quiz_item(
            subtype="multiple_choice",
            choices=["Integration of arms.", "Random answer"],
            correct_answer="A",
        ),
    ]

    validated, _report = validate_assessment_items(
        items=items,
        concepts=[_concept()],
        segment_ids={"seg-1"},
        wiki_ids={"wiki-1"},
    )

    assert len(validated) == 1
    assert validated[0]["correct_answer"] == "Integration of arms."
