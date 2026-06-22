from app.pipeline import build_pipeline, derive_qngen_assessment_types


def test_build_pipeline_always_includes_intellex_steps() -> None:
    pipeline = build_pipeline([])

    step_names = [step["step"] for step in pipeline]

    assert step_names == [
        "store",
        "parse",
        "normalize-document",
        "trim-document-boundaries",
        "structure-document",
        "validate-structure",
        "chunk",
        "source-research",
        "extract-knowledge",
    ]


def test_build_pipeline_appends_selected_targets() -> None:
    pipeline = build_pipeline(
        ["eleven_reader_script", "flashcards", "quizzes", "scenarios"],
    )

    step_names = [step["step"] for step in pipeline]

    assert step_names[-4:] == [
        "create-ebook",
        "generate-flashcards",
        "generate-questions",
        "generate-scenarios",
    ]


def test_eleven_reader_target_maps_to_create_ebook() -> None:
    pipeline = build_pipeline(["eleven_reader_script"])
    create_ebook = next(step for step in pipeline if step["step"] == "create-ebook")

    assert create_ebook["module"] == "mathesys"
    assert create_ebook["stage_id"] == "create-ebook"


def test_prepare_and_deconstruct_are_gone() -> None:
    step_names = [step["step"] for step in build_pipeline([])]

    assert "prepare-document" not in step_names
    assert "deconstruct-document" not in step_names


def test_derive_qngen_assessment_types() -> None:
    assert derive_qngen_assessment_types(["flashcards", "eleven_reader_script"]) == [
        "flashcards",
    ]
    assert derive_qngen_assessment_types(
        ["flashcards", "quizzes", "scenarios"],
    ) == ["flashcards", "quizzes", "scenarios"]
