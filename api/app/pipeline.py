from copy import deepcopy
from typing import Any

BASE_PIPELINE: list[dict[str, Any]] = [
    {
        "step": "store",
        "type": "deterministic",
        "status": "pending",
    },
    {
        "step": "parse",
        "type": "deterministic",
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
        "step": "chunk",
        "type": "deterministic",
        "status": "pending",
    },
    {
        "step": "document-deconstructor",
        "type": "skill",
        "module": "intellex",
        "skill_id": "document-deconstructor",
        "skill_version": "1.0.0",
        "status": "pending",
    },
]

OPTIONAL_PIPELINE_STEPS: dict[str, dict[str, Any]] = {
    "eleven_reader_script": {
        "step": "eleven-reader-script",
        "type": "skill",
        "module": "mathesys",
        "skill_id": "eleven-reader-script",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "flashcards": {
        "step": "flashcard-gen",
        "type": "skill",
        "module": "qngen",
        "skill_id": "flashcard-gen",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "quizzes": {
        "step": "quiz-gen",
        "type": "skill",
        "module": "qngen",
        "skill_id": "quiz-gen",
        "skill_version": "1.0.0",
        "status": "pending",
    },
    "scenarios": {
        "step": "scenario-gen",
        "type": "skill",
        "module": "qngen",
        "skill_id": "scenario-gen",
        "skill_version": "1.0.0",
        "status": "pending",
    },
}

SUPPORTED_TARGET_ARTIFACTS = frozenset(OPTIONAL_PIPELINE_STEPS.keys())


def build_pipeline(target_artifacts: list[str]) -> list[dict[str, Any]]:
    pipeline = [deepcopy(step) for step in BASE_PIPELINE]

    for artifact in target_artifacts:
        optional_step = OPTIONAL_PIPELINE_STEPS.get(artifact)

        if optional_step:
            pipeline.append(deepcopy(optional_step))

    return pipeline
