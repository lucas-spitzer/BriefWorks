from copy import deepcopy
from typing import Any

BASE_PIPELINE: list[dict[str, Any]] = [
    {
        "step": "store",
        "type": "deterministic",
        "module": "intellex",
        "status": "pending",
    },
    {
        "step": "parse",
        "type": "stage",
        "module": "intellex",
        "stage_id": "parse",
        "stage_version": "1.0.0",
        "status": "pending",
    },
    {
        "step": "prepare-document",
        "type": "stage",
        "module": "intellex",
        "stage_id": "prepare-document",
        "stage_version": "2.0.0",
        "status": "pending",
    },
    {
        "step": "chunk",
        "type": "deterministic",
        "module": "intellex",
        "status": "pending",
    },
    {
        "step": "source-research",
        "type": "stage",
        "module": "intellex",
        "stage_id": "source-research",
        "stage_version": "1.0.0",
        "status": "pending",
    },
    {
        "step": "deconstruct-document",
        "type": "stage",
        "module": "intellex",
        "stage_id": "deconstruct-document",
        "stage_version": "2.0.0",
        "status": "pending",
    },
    {
        "step": "extract-knowledge",
        "type": "stage",
        "module": "intellex",
        "stage_id": "extract-knowledge",
        "stage_version": "1.0.0",
        "status": "pending",
    },
]

OPTIONAL_PIPELINE_STEPS: dict[str, dict[str, Any]] = {
    "eleven_reader_script": {
        "step": "elevenreader-ebook",
        "type": "stage",
        "module": "mathesys",
        "stage_id": "elevenreader-ebook",
        "stage_version": "2.0.0",
        "status": "pending",
    },
    "speechify_audio": {
        "step": "speechify-audio",
        "type": "stage",
        "module": "mathesys",
        "stage_id": "speechify-audio",
        "stage_version": "1.0.0",
        "status": "pending",
    },
    "elevenlabs_audio": {
        "step": "elevenlabs-audio",
        "type": "stage",
        "module": "mathesys",
        "stage_id": "elevenlabs-audio",
        "stage_version": "1.0.0",
        "status": "pending",
    },
    "flashcards": {
        "step": "generate-flashcards",
        "type": "stage",
        "module": "qngen",
        "stage_id": "generate-flashcards",
        "stage_version": "1.0.0",
        "status": "pending",
    },
    "quizzes": {
        "step": "generate-questions",
        "type": "stage",
        "module": "qngen",
        "stage_id": "generate-questions",
        "stage_version": "1.0.0",
        "status": "pending",
    },
    "scenarios": {
        "step": "generate-scenarios",
        "type": "stage",
        "module": "qngen",
        "stage_id": "generate-scenarios",
        "stage_version": "1.0.0",
        "status": "pending",
    },
}

QNGEN_TARGET_ARTIFACTS = frozenset({"flashcards", "quizzes", "scenarios"})

SUPPORTED_TARGET_ARTIFACTS = frozenset(OPTIONAL_PIPELINE_STEPS.keys())


def derive_qngen_assessment_types(target_artifacts: list[str]) -> list[str]:
    return [
        artifact
        for artifact in ("flashcards", "quizzes", "scenarios")
        if artifact in target_artifacts
    ]


def build_pipeline(target_artifacts: list[str]) -> list[dict[str, Any]]:
    pipeline = [deepcopy(step) for step in BASE_PIPELINE]

    for artifact in target_artifacts:
        optional_step = OPTIONAL_PIPELINE_STEPS.get(artifact)

        if optional_step:
            pipeline.append(deepcopy(optional_step))

    return pipeline
