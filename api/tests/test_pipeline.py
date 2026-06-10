from app.pipeline import build_pipeline


def test_build_pipeline_always_includes_intellex_steps() -> None:
    pipeline = build_pipeline([])

    step_names = [step["step"] for step in pipeline]

    assert step_names == [
        "store",
        "parse",
        "source-research",
        "chunk",
        "document-deconstructor",
    ]


def test_build_pipeline_appends_selected_targets() -> None:
    pipeline = build_pipeline(
        ["eleven_reader_script", "flashcards", "quizzes", "scenarios"],
    )

    step_names = [step["step"] for step in pipeline]

    assert step_names[-4:] == [
        "eleven-reader-script",
        "flashcard-gen",
        "quiz-gen",
        "scenario-gen",
    ]
