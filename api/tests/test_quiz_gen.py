import app.qngen.stages.quiz_gen as quiz_gen_module
from app.qngen.canonical_context import ConceptCard
from app.qngen.stages.quiz_gen import QuizGenStage


def _concept(wiki_id: str, label: str, segment_ids: list[str]) -> ConceptCard:
    return ConceptCard(
        wiki_id=wiki_id,
        preferred_label=label,
        definition=f"Definition for {label}",
        importance="essential",
        evidence_segment_ids=segment_ids,
        evidence_segments=[
            {"segment_id": sid, "kind": "paragraph", "text": "t", "page": 1}
            for sid in segment_ids
        ],
    )


def _quiz_item(concept: ConceptCard) -> dict:
    return {
        "item_id": f"q-{concept.wiki_id}",
        "type": "quiz",
        "subtype": "multiple_choice",
        "question": f"What is {concept.preferred_label}?",
        "choices": [concept.definition, "Something else"],
        "correct_answer": concept.definition,
        "wiki_ids_cited": [concept.wiki_id],
        "source_chunk_ids": concept.evidence_segment_ids,
    }


def _source_metadata() -> dict:
    return {
        "extract": {
            "chapters": [
                {
                    "chapter_id": "ch-1",
                    "chapter_title": "Foundations",
                    "sequence_index": 1,
                    "segment_ids": ["seg-1"],
                    "objectives": [
                        {
                            "objective_id": "obj-1",
                            "statement": "Define war",
                            "bloom_level": "understand",
                            "concept_labels": ["War"],
                        },
                    ],
                },
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
            ],
        },
    }


def test_blueprint_path_generates_objective_driven_questions(monkeypatch) -> None:
    captured: dict = {}

    concepts = [
        _concept("wiki-war", "War", ["seg-1"]),
        _concept("wiki-tempo", "Tempo", ["seg-3"]),
    ]

    def fake_run_blueprinted_generation(*, skill_name, artifact_type, blueprint, count_band=None, **_kwargs):
        captured["skill_name"] = skill_name
        captured["artifact_type"] = artifact_type
        captured["chapter_ids"] = [c.chapter_id for c in blueprint]
        captured["count_band"] = count_band
        return [_quiz_item(c) for c in concepts], {
            "model": "m",
            "provider": "p",
            "token_usage": {"total_tokens": 1},
            "batch_count": 2,
            "generation_mode": "blueprint",
        }

    monkeypatch.setattr(
        quiz_gen_module, "run_blueprinted_generation", fake_run_blueprinted_generation,
    )

    output, execution = QuizGenStage().run(
        source_metadata=_source_metadata(),
        concepts=concepts,
        concept_batches=[],
        learning_objectives=[],
    )

    assert execution["generation_mode"] == "blueprint"
    assert captured["skill_name"] == "questions"
    # Questions are deterministically objective-driven: no count band.
    assert captured["count_band"] is None
    assert captured["chapter_ids"] == ["ch-1", "ch-2"]
    assert {q.question for q in output.questions} == {"What is War?", "What is Tempo?"}


def test_falls_back_to_legacy_when_blueprint_yields_nothing(monkeypatch) -> None:
    # Chapters exist but the chapter↔concept join produced no items (e.g. orphan
    # evidence segments): the stage must fall back rather than ship zero questions.
    concept = _concept("wiki-war", "War", ["seg-1"])

    monkeypatch.setattr(
        quiz_gen_module,
        "run_blueprinted_generation",
        lambda **_kwargs: ([], {"batch_count": 0, "generation_mode": "blueprint"}),
    )

    legacy_called: list[bool] = []

    def fake_run_skill_generation(**_kwargs):
        legacy_called.append(True)
        return [_quiz_item(concept)], {"model": "m", "token_usage": {}, "batch_count": 1}

    monkeypatch.setattr(quiz_gen_module, "run_skill_generation", fake_run_skill_generation)

    output, execution = QuizGenStage().run(
        source_metadata=_source_metadata(),
        concepts=[concept],
        concept_batches=[[concept]],
        learning_objectives=[],
    )

    assert legacy_called == [True]
    assert len(output.questions) == 1
    assert "generation_mode" not in execution


def test_falls_back_to_concept_batches_without_chapters(monkeypatch) -> None:
    concept = _concept("wiki-war", "War", ["seg-1"])

    def fake_run_skill_generation(**_kwargs):
        return [_quiz_item(concept)], {
            "model": "m",
            "token_usage": {},
            "batch_count": 1,
        }

    monkeypatch.setattr(quiz_gen_module, "run_skill_generation", fake_run_skill_generation)

    output, execution = QuizGenStage().run(
        source_metadata={},
        concepts=[concept],
        concept_batches=[[concept]],
        learning_objectives=[],
    )

    assert len(output.questions) == 1
    assert "generation_mode" not in execution
