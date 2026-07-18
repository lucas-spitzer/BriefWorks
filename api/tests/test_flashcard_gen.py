import app.qngen.stages.flashcard_gen as flashcard_gen_module
from app.qngen.canonical_context import ConceptCard
from app.qngen.stages.flashcard_gen import FlashcardGenStage


def _concept(
    wiki_id: str,
    label: str,
    segment_ids: list[str],
    importance: str = "essential",
) -> ConceptCard:
    return ConceptCard(
        wiki_id=wiki_id,
        preferred_label=label,
        definition=f"Definition for {label}",
        importance=importance,
        evidence_segment_ids=segment_ids,
        evidence_segments=[
            {"segment_id": sid, "kind": "paragraph", "text": "t", "page": 1}
            for sid in segment_ids
        ],
    )


def _flashcard_item(concept: ConceptCard) -> dict:
    return {
        "item_id": f"fc-{concept.wiki_id}",
        "type": "flashcard",
        "subtype": "term_definition",
        "front": concept.preferred_label,
        "back": concept.definition,
        "wiki_ids_cited": [concept.wiki_id],
        "source_chunk_ids": concept.evidence_segment_ids,
    }


def _chapters() -> list[dict]:
    return [
        {
            "chapter_id": "ch-1",
            "chapter_title": "Foundations",
            "sequence_index": 1,
            "segment_ids": ["seg-1"],
            "objectives": [],
        },
    ]


def test_blueprint_passes_importance_floor_and_count_band(monkeypatch) -> None:
    captured: dict = {}
    concept = _concept("wiki-war", "War", ["seg-1"])

    def fake_run_blueprinted_generation(*, skill_name, concept_filter, count_band, **_kwargs):
        captured["skill_name"] = skill_name
        captured["concept_filter"] = concept_filter
        captured["count_band"] = count_band
        return [_flashcard_item(concept)], {
            "model": "m",
            "provider": "p",
            "token_usage": {"total_tokens": 1},
            "batch_count": 1,
            "generation_mode": "blueprint",
        }

    monkeypatch.setattr(
        flashcard_gen_module,
        "run_blueprinted_generation",
        fake_run_blueprinted_generation,
    )

    output, execution = FlashcardGenStage().run(
        source_metadata={},
        concepts=[concept],
        concept_batches=[],
        learning_objectives=[],
        chapters=_chapters(),
    )

    assert execution["generation_mode"] == "blueprint"
    assert captured["skill_name"] == "flashcards"
    assert captured["count_band"] == (3, 8)

    keep = captured["concept_filter"]
    assert keep(_concept("a", "A", ["seg-1"], importance="essential")) is True
    assert keep(_concept("b", "B", ["seg-1"], importance="supporting")) is True
    assert keep(_concept("c", "C", ["seg-1"], importance="contextual")) is False

    assert [fc.front for fc in output.flashcards] == ["War"]


def test_falls_back_to_concept_batches_without_chapters(monkeypatch) -> None:
    concept = _concept("wiki-war", "War", ["seg-1"])

    def fake_run_skill_generation(**_kwargs):
        return [_flashcard_item(concept)], {
            "model": "m",
            "token_usage": {},
            "batch_count": 1,
        }

    monkeypatch.setattr(
        flashcard_gen_module, "run_skill_generation", fake_run_skill_generation,
    )

    output, execution = FlashcardGenStage().run(
        source_metadata={},
        concepts=[concept],
        concept_batches=[[concept]],
        learning_objectives=[],
    )

    assert len(output.flashcards) == 1
    assert "generation_mode" not in execution
