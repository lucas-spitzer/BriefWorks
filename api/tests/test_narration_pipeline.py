from app.pipeline import SUPPORTED_TARGET_ARTIFACTS, build_pipeline


def test_supported_target_artifacts_include_narration_outputs() -> None:
    assert {
        "eleven_reader_script",
        "speechify_script",
        "speechify_audio",
        "elevenlabs_audio",
    }.issubset(SUPPORTED_TARGET_ARTIFACTS)


def test_build_pipeline_appends_narration_steps() -> None:
    pipeline = build_pipeline(
        [
            "eleven_reader_script",
            "speechify_script",
            "speechify_audio",
            "elevenlabs_audio",
        ],
    )

    step_names = [step["step"] for step in pipeline]

    assert step_names[-4:] == [
        "eleven-reader-script",
        "speechify-app-epub",
        "speechify-api-ssml",
        "elevenlabs-structured-text",
    ]
