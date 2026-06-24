from app.qngen.skills.flashcards.helpers import prefer_term_definition


def _card(*, wiki_id: str, front: str, subtype: str = "term_definition", **extra) -> dict:
    return {
        "item_id": f"item-{wiki_id}-{front}",
        "type": "flashcard",
        "subtype": subtype,
        "wiki_ids_cited": [wiki_id],
        "front": front,
        "back": extra.get("back", f"Definition of {front}."),
        "source_chunk_ids": extra.get("source_chunk_ids", ["seg-1"]),
    }


def test_dedup_collapses_case_variant_terms() -> None:
    # Two canonical entries differing only in casing escaped wiki dedup before.
    items = [
        _card(wiki_id="wiki-1", front="Enemy system"),
        _card(wiki_id="wiki-2", front="enemy system"),
    ]

    result = prefer_term_definition(items)

    assert len(result) == 1
    assert result[0]["front"] == "Enemy system"


def test_dedup_keeps_best_grounded_card_on_collision() -> None:
    sparse = _card(wiki_id="wiki-1", front="Tempo", source_chunk_ids=["seg-1"])
    grounded = _card(
        wiki_id="wiki-2",
        front="tempo",
        source_chunk_ids=["seg-1", "seg-2", "seg-3"],
    )

    result = prefer_term_definition([sparse, grounded])

    assert len(result) == 1
    assert result[0]["front"] == "tempo"


def test_dedup_still_collapses_by_wiki_id() -> None:
    items = [
        _card(wiki_id="wiki-1", front="Tempo"),
        _card(wiki_id="wiki-1", front="What is tempo?", subtype="basic"),
    ]

    result = prefer_term_definition(items)

    assert len(result) == 1
    assert result[0]["subtype"] == "term_definition"


def test_dedup_keeps_distinct_terms() -> None:
    items = [
        _card(wiki_id="wiki-1", front="Tempo"),
        _card(wiki_id="wiki-2", front="Surprise"),
    ]

    result = prefer_term_definition(items)

    assert {card["front"] for card in result} == {"Tempo", "Surprise"}
