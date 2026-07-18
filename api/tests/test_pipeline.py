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
        "web-enrichment",
    ]


def test_build_pipeline_appends_selected_targets() -> None:
    pipeline = build_pipeline(
        ["electronic_book", "flashcards", "quizzes", "scenarios"],
    )

    step_names = [step["step"] for step in pipeline]

    assert step_names[-4:] == [
        "create-ebook",
        "generate-flashcards",
        "generate-questions",
        "generate-scenarios",
    ]


def test_electronic_book_target_maps_to_create_ebook() -> None:
    pipeline = build_pipeline(["electronic_book"])
    create_ebook = next(step for step in pipeline if step["step"] == "create-ebook")

    assert create_ebook["module"] == "mathesys"
    assert create_ebook["stage_id"] == "create-ebook"


def test_prepare_and_deconstruct_are_gone() -> None:
    step_names = [step["step"] for step in build_pipeline([])]

    assert "prepare-document" not in step_names
    assert "deconstruct-document" not in step_names


def test_extract_knowledge_is_gone() -> None:
    # Wiki entries are curated manually via the authoring flow, not extracted.
    step_names = [step["step"] for step in build_pipeline([])]

    assert "extract-knowledge" not in step_names


def test_wiki_json_target_maps_to_export_stage() -> None:
    pipeline = build_pipeline(["wiki_json"])
    export_step = next(step for step in pipeline if step["step"] == "export-wiki-json")

    assert export_step["module"] == "mathesys"
    assert export_step["stage_id"] == "export-wiki-json"


def test_derive_qngen_assessment_types() -> None:
    assert derive_qngen_assessment_types(["flashcards", "electronic_book"]) == [
        "flashcards",
    ]
    assert derive_qngen_assessment_types(
        ["flashcards", "quizzes", "scenarios"],
    ) == ["flashcards", "quizzes", "scenarios"]
