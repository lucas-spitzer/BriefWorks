import app.qngen.stages.scenario_gen as scenario_gen_module
from app.qngen.canonical_context import ConceptCard
from app.qngen.stages.scenario_gen import ScenarioGenStage


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


def _scenario_item(concept: ConceptCard) -> dict:
    return {
        "item_id": f"s-{concept.wiki_id}",
        "type": "scenario",
        "subtype": "decision_prompt",
        "title": f"{concept.preferred_label} dilemma",
        "situation": "A pressing situation.",
        "task": f"Decide how to apply {concept.preferred_label}.",
        "expected_response_elements": ["apply the concept"],
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
        {
            "chapter_id": "ch-2",
            "chapter_title": "Maneuver",
            "sequence_index": 2,
            "segment_ids": ["seg-3"],
            "objectives": [],
        },
    ]


def test_blueprint_passes_essential_filter_and_count_band(monkeypatch) -> None:
    captured: dict = {}

    def fake_run_blueprinted_generation(*, skill_name, concept_filter, count_band, **_kwargs):
        captured["skill_name"] = skill_name
        captured["concept_filter"] = concept_filter
        captured["count_band"] = count_band
        return [_scenario_item(_concept("wiki-war", "War", ["seg-1"]))], {
            "model": "m",
            "provider": "p",
            "token_usage": {"total_tokens": 1},
            "batch_count": 1,
            "generation_mode": "blueprint",
        }

    monkeypatch.setattr(
        scenario_gen_module,
        "run_blueprinted_generation",
        fake_run_blueprinted_generation,
    )

    concepts = [
        _concept("wiki-war", "War", ["seg-1"], importance="essential"),
        _concept("wiki-tempo", "Tempo", ["seg-3"], importance="supporting"),
    ]

    output, execution = ScenarioGenStage().run(
        source_metadata={},
        concepts=concepts,
        concept_batches=[],
        learning_objectives=[],
        chapters=_chapters(),
    )

    assert execution["generation_mode"] == "blueprint"
    assert captured["skill_name"] == "scenarios"
    assert captured["count_band"] == (1, 3)
    # The filter keeps essential concepts and drops the rest.
    keep = captured["concept_filter"]
    assert keep(concepts[0]) is True
    assert keep(concepts[1]) is False
    assert [s.title for s in output.scenarios] == ["War dilemma"]


def test_blueprint_with_no_essential_concepts_returns_empty(monkeypatch) -> None:
    def fake_run_blueprinted_generation(**_kwargs):
        return [], {
            "model": "",
            "provider": "",
            "token_usage": {},
            "batch_count": 0,
            "generation_mode": "blueprint",
        }

    monkeypatch.setattr(
        scenario_gen_module,
        "run_blueprinted_generation",
        fake_run_blueprinted_generation,
    )

    concepts = [
        _concept("wiki-tempo", "Tempo", ["seg-3"], importance="supporting"),
    ]

    output, execution = ScenarioGenStage().run(
        source_metadata={},
        concepts=concepts,
        concept_batches=[],
        learning_objectives=[],
        chapters=_chapters(),
    )

    assert output.scenarios == []
    assert execution["validation_report"]["skipped"] == "no essential concepts"


def test_falls_back_to_essential_batches_without_chapters(monkeypatch) -> None:
    concept = _concept("wiki-war", "War", ["seg-1"], importance="essential")

    def fake_run_skill_generation(**_kwargs):
        return [_scenario_item(concept)], {
            "model": "m",
            "token_usage": {},
            "batch_count": 1,
        }

    monkeypatch.setattr(
        scenario_gen_module, "run_skill_generation", fake_run_skill_generation,
    )

    output, execution = ScenarioGenStage().run(
        source_metadata={},
        concepts=[concept],
        concept_batches=[[concept]],
        learning_objectives=[],
    )

    assert len(output.scenarios) == 1
    assert "generation_mode" not in execution
