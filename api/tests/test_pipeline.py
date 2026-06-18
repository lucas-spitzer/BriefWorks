from app.pipeline import build_pipeline, derive_qngen_assessment_types


def test_build_pipeline_always_includes_intellex_steps() -> None:
    pipeline = build_pipeline([])

    step_names = [step["step"] for step in pipeline]

    assert step_names == [
        "store",
        "parse",
        "prepare-document",
        "chunk",
        "source-research",
        "deconstruct-document",
        "extract-knowledge",
    ]


def test_build_pipeline_appends_selected_targets() -> None:
    pipeline = build_pipeline(
        ["eleven_reader_script", "flashcards", "quizzes", "scenarios"],
    )

    step_names = [step["step"] for step in pipeline]

    assert step_names[-4:] == [
        "elevenreader-ebook",
        "generate-flashcards",
        "generate-questions",
        "generate-scenarios",
    ]


def test_derive_qngen_assessment_types() -> None:
    assert derive_qngen_assessment_types(["flashcards", "eleven_reader_script"]) == [
        "flashcards",
    ]
    assert derive_qngen_assessment_types(
        ["flashcards", "quizzes", "scenarios"],
    ) == ["flashcards", "quizzes", "scenarios"]
