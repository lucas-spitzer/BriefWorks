from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.qngen.canonical_context import ConceptCard, build_chapter_blueprint
from app.qngen.skills.scenarios.helpers import filter_essential_only
from app.qngen.skills.shared.item_mapping import (
    assessment_item_to_scenario,
    ensure_item_ids,
)
from app.qngen.skills.shared.orchestrator import (
    run_blueprinted_generation,
    run_skill_generation,
)
from app.qngen.stages.models import GeneratedScenario, ScenarioGenOutput
from app.qngen.validators import validate_assessment_items


def _empty_execution(reason: str) -> dict[str, Any]:
    return {
        "model": "deterministic-passthrough",
        "provider": "local",
        "token_usage": {},
        "batch_count": 0,
        "validation_report": {
            "input_count": 0,
            "validated_count": 0,
            "skipped": reason,
        },
    }


class ScenarioGenStage:
    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        concepts: list[ConceptCard],
        concept_batches: list[list[ConceptCard]],
        learning_objectives: list[dict[str, Any]],
        chapters: list[dict[str, Any]] | None = None,
    ) -> tuple[ScenarioGenOutput, dict[str, Any]]:
        blueprint = build_chapter_blueprint(chapters or [], concepts)

        raw_items: list[dict[str, Any]] = []
        execution: dict[str, Any] = {}
        if blueprint:
            settings = get_settings()
            raw_items, execution = run_blueprinted_generation(
                skill_name="scenarios",
                artifact_type="scenario",
                source_metadata=source_metadata,
                blueprint=blueprint,
                concept_filter=lambda concept: concept.importance == "essential",
                count_band=(
                    settings.qngen.scenarios_per_chapter_min,
                    settings.qngen.scenarios_per_chapter_max,
                ),
            )

        if not raw_items:
            # No chapter structure, or the chapter↔concept join produced nothing
            # (e.g. essential concepts whose evidence sits in unassigned
            # segments): fall back to essential concept batches so a broken
            # blueprint can't silently zero out scenarios.
            essential_batches = [
                [concept for concept in batch if concept.importance == "essential"]
                for batch in concept_batches
            ]
            essential_batches = [batch for batch in essential_batches if batch]

            if not essential_batches:
                return ScenarioGenOutput(scenarios=[]), _empty_execution(
                    "no essential concepts",
                )

            raw_items, execution = run_skill_generation(
                skill_name="scenarios",
                artifact_type="scenario",
                source_metadata=source_metadata,
                concept_batches=essential_batches,
                learning_objectives=learning_objectives,
            )

        essential_wiki_ids = {
            concept.wiki_id for concept in concepts if concept.importance == "essential"
        }
        raw_items = filter_essential_only(
            ensure_item_ids(raw_items),
            essential_wiki_ids=essential_wiki_ids,
        )

        wiki_ids = {concept.wiki_id for concept in concepts}
        segment_ids = {
            segment_id
            for concept in concepts
            for segment_id in concept.evidence_segment_ids
        }

        validated, validation_report = validate_assessment_items(
            items=raw_items,
            concepts=concepts,
            segment_ids=segment_ids,
            wiki_ids=wiki_ids,
        )
        scenarios = [
            GeneratedScenario.model_validate(assessment_item_to_scenario(item))
            for item in validated
            if item.get("type") == "scenario"
        ]

        execution["validation_report"] = validation_report
        return ScenarioGenOutput(scenarios=scenarios), execution
