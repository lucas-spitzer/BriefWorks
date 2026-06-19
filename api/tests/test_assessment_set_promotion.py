from app.qngen.assessment_set_promotion import promote_assessment_set


def test_promote_assessment_set_builds_canonical_and_denormalized_rows() -> None:
    items = [
        {
            "item_id": "item-1",
            "type": "flashcard",
            "subtype": "term_definition",
            "difficulty": "easy",
            "front": "What is Combined Arms?",
            "back": "Integration of arms.",
            "wiki_ids_cited": ["wiki-1"],
            "source_chunk_ids": ["seg-1"],
            "tags": ["doctrine"],
        },
        {
            "item_id": "item-2",
            "type": "quiz",
            "subtype": "multiple_choice",
            "difficulty": "medium",
            "question": "Which best describes combined arms?",
            "choices": ["Force dilemma", "Avoid maneuver"],
            "correct_answer": "Force dilemma",
            "explanation": "Combined arms creates dilemmas.",
            "wiki_ids_cited": ["wiki-1"],
            "source_chunk_ids": ["seg-1"],
            "tags": [],
        },
        {
            "item_id": "item-3",
            "type": "scenario",
            "subtype": "decision_prompt",
            "difficulty": "hard",
            "situation": "Limited visibility.",
            "task": "Apply combined arms.",
            "expected_response_elements": ["Suppress", "Maneuver"],
            "rubric": {"excellent": "Integrates fires and maneuver."},
            "wiki_ids_cited": ["wiki-1"],
            "source_chunk_ids": ["seg-1"],
            "tags": [],
        },
    ]

    set_row, flashcards, quizzes, scenarios = promote_assessment_set(
        workspace_id="ws-1",
        source_id="src-1",
        production_run_id="run-1",
        stage_run_id="stage-1",
        stage_id="assessment-set-gen",
        stage_version="1.0.0",
        source_metadata={"research": {"title": "Combined Arms"}},
        assessment_types=["flashcards", "quizzes", "scenarios"],
        items=items,
        assessment_set_id="set-1",
    )

    assert set_row["id"] == "set-1"
    assert set_row["title"] == "Assessment Set: Combined Arms"
    assert len(set_row["items"]) == 3
    assert flashcards[0]["assessment_set_id"] == "set-1"
    assert flashcards[0]["item_id"] == "item-1"
    assert flashcards[0]["subtype"] == "term_definition"
    assert quizzes[0]["question_type"] == "multiple_choice"
    assert scenarios[0]["prompt"] == "Apply combined arms."
    assert scenarios[0]["rubric"]["excellent"] == "Integrates fires and maneuver."
