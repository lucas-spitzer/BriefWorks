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
        "type": "deterministic",
        "module": "intellex",
        "status": "pending",
    },
    {
        "step": "prepare-document",
        "type": "skill",
        "module": "intellex",
        "skill_id": "prepare-document",
        "skill_version": "2.0.0",
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
        "type": "skill",
        "module": "intellex",
        "skill_id": "source-research",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    {
        "step": "deconstruct-document",
        "type": "skill",
        "module": "intellex",
        "skill_id": "deconstruct-document",
        "skill_version": "2.0.0",
        "status": "pending",
    },
    {
        "step": "extract-knowledge",
        "type": "skill",
        "module": "intellex",
        "skill_id": "extract-knowledge",
        "skill_version": "1.0.0",
        "status": "pending",
    },
]

OPTIONAL_PIPELINE_STEPS: dict[str, dict[str, Any]] = {
    "eleven_reader_script": {
        "step": "elevenreader-ebook",
        "type": "skill",
        "module": "mathesys",
        "skill_id": "elevenreader-ebook",
        "skill_version": "2.0.0",
        "status": "pending",
    },
    "speechify_audio": {
        "step": "speechify-audio",
        "type": "skill",
        "module": "mathesys",
        "skill_id": "speechify-audio",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "elevenlabs_audio": {
        "step": "elevenlabs-audio",
        "type": "skill",
        "module": "mathesys",
        "skill_id": "elevenlabs-audio",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "flashcards": {
        "step": "generate-flashcards",
        "type": "skill",
        "module": "qngen",
        "skill_id": "generate-flashcards",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "quizzes": {
        "step": "generate-questions",
        "type": "skill",
        "module": "qngen",
        "skill_id": "generate-questions",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "scenarios": {
        "step": "generate-scenarios",
        "type": "skill",
        "module": "qngen",
        "skill_id": "generate-scenarios",
        "skill_version": "1.0.0",
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
