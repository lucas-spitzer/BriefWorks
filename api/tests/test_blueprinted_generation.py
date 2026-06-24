import app.qngen.skills.shared.orchestrator as orchestrator
from app.qngen.canonical_context import ChapterBlueprint, ConceptCard
from app.qngen.skills.shared.orchestrator import run_blueprinted_generation


def _concept(wiki_id: str, label: str, importance: str) -> ConceptCard:
    return ConceptCard(
        wiki_id=wiki_id,
        preferred_label=label,
        definition=f"Definition for {label}",
        importance=importance,
        evidence_segment_ids=["seg-1"],
        evidence_segments=[
            {"segment_id": "seg-1", "kind": "paragraph", "text": "t", "page": 1},
        ],
    )


def _chapter(chapter_id: str, sequence_index: int, concepts: list[ConceptCard]) -> ChapterBlueprint:
    return ChapterBlueprint(
        chapter_id=chapter_id,
        chapter_title=chapter_id,
        sequence_index=sequence_index,
        segment_ids=["seg-1"],
        concepts=concepts,
        objectives=[],
    )


def test_runner_skips_chapters_with_no_matching_concepts(monkeypatch) -> None:
    seen: list[dict] = []

    def fake_run_skill_batch(*, concepts, count_band, **_kwargs):
        seen.append({"concepts": [c.wiki_id for c in concepts], "count_band": count_band})
        return [{"item_id": concepts[0].wiki_id, "type": "scenario"}], {
            "model": "m",
            "provider": "p",
            "token_usage": {"total_tokens": 1},
        }

    monkeypatch.setattr(orchestrator, "run_skill_batch", fake_run_skill_batch)

    blueprint = [
        _chapter("ch-1", 1, [_concept("wiki-war", "War", "essential")]),
        _chapter("ch-2", 2, [_concept("wiki-tempo", "Tempo", "supporting")]),
    ]

    items, execution = run_blueprinted_generation(
        skill_name="scenarios",
        artifact_type="scenario",
        source_metadata={},
        blueprint=blueprint,
        concept_filter=lambda concept: concept.importance == "essential",
        count_band=(1, 3),
    )

    # Only the chapter with an essential concept generated.
    assert seen == [{"concepts": ["wiki-war"], "count_band": (1, 3)}]
    assert execution["batch_count"] == 1
    assert execution["generation_mode"] == "blueprint"
    assert len(items) == 1


def test_runner_without_filter_uses_all_concepts(monkeypatch) -> None:
    seen: list[list[str]] = []

    def fake_run_skill_batch(*, concepts, **_kwargs):
        seen.append([c.wiki_id for c in concepts])
        return [], {"model": "m", "provider": "p", "token_usage": {}}

    monkeypatch.setattr(orchestrator, "run_skill_batch", fake_run_skill_batch)

    blueprint = [
        _chapter(
            "ch-1",
            1,
            [
                _concept("wiki-war", "War", "essential"),
                _concept("wiki-tempo", "Tempo", "supporting"),
            ],
        ),
    ]

    run_blueprinted_generation(
        skill_name="questions",
        artifact_type="quiz",
        source_metadata={},
        blueprint=blueprint,
    )

    assert seen == [["wiki-war", "wiki-tempo"]]
