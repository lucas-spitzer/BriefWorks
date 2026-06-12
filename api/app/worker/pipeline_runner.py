from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.intellex.ingest import chunk_parsed_document, parse_source_content
from app.intellex.models import ParsedDocument
from app.worker.db import WorkerDatabase
from app.worker.skill_executor import (
    DocumentDeconstructorSkillExecutor,
    ElevenLabsStructuredTextSkillExecutor,
    ElevenReaderScriptSkillExecutor,
    FlashcardGenSkillExecutor,
    QuizGenSkillExecutor,
    ScenarioGenSkillExecutor,
    SourceResearchSkillExecutor,
    SpeechifyApiSsmlSkillExecutor,
    SpeechifyAppEpubSkillExecutor,
)
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def mark_step(
    pipeline: list[dict[str, Any]],
    step_name: str,
    *,
    status: str,
    skill_run_id: str | None = None,
    detail: str | None = None,
) -> list[dict[str, Any]]:
    updated_pipeline: list[dict[str, Any]] = []

    for step in pipeline:
        next_step = copy.deepcopy(step)

        if next_step.get("step") == step_name:
            next_step["status"] = status

            if skill_run_id:
                next_step["skill_run_id"] = skill_run_id

            if detail:
                next_step["detail"] = detail

        updated_pipeline.append(next_step)

    return updated_pipeline


@dataclass
class PipelineContext:
    production_run_id: str
    workspace_id: str
    sources: list[dict[str, Any]]
    parsed_documents: dict[str, ParsedDocument] = field(default_factory=dict)
    target_artifacts: list[str] = field(default_factory=list)


class PipelineRunner:
    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        source_research: SourceResearchSkillExecutor | None = None,
        document_deconstructor: DocumentDeconstructorSkillExecutor | None = None,
        eleven_reader_script: ElevenReaderScriptSkillExecutor | None = None,
        speechify_app_epub: SpeechifyAppEpubSkillExecutor | None = None,
        speechify_api_ssml: SpeechifyApiSsmlSkillExecutor | None = None,
        elevenlabs_structured_text: ElevenLabsStructuredTextSkillExecutor | None = None,
        flashcard_gen: FlashcardGenSkillExecutor | None = None,
        quiz_gen: QuizGenSkillExecutor | None = None,
        scenario_gen: ScenarioGenSkillExecutor | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.source_research = source_research or SourceResearchSkillExecutor(self.db)
        self.document_deconstructor = document_deconstructor or DocumentDeconstructorSkillExecutor(self.db)
        self.eleven_reader_script = eleven_reader_script or ElevenReaderScriptSkillExecutor(
            self.db,
            self.storage,
        )
        self.speechify_app_epub = speechify_app_epub or SpeechifyAppEpubSkillExecutor(
            self.db,
            self.storage,
        )
        self.speechify_api_ssml = speechify_api_ssml or SpeechifyApiSsmlSkillExecutor(
            self.db,
            self.storage,
        )
        self.elevenlabs_structured_text = (
            elevenlabs_structured_text
            or ElevenLabsStructuredTextSkillExecutor(self.db, self.storage)
        )
        self.flashcard_gen = flashcard_gen or FlashcardGenSkillExecutor(self.db)
        self.quiz_gen = quiz_gen or QuizGenSkillExecutor(self.db)
        self.scenario_gen = scenario_gen or ScenarioGenSkillExecutor(self.db)

    def run_store_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unstored = [
            source["id"]
            for source in context.sources
            if not source.get("storage_path")
        ]

        if unstored:
            raise RuntimeError(f"Sources missing storage paths: {', '.join(unstored)}")

        return mark_step(pipeline, "store", status="completed")

    def run_parse_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for source in context.sources:
            source_id = source["id"]
            self.db.update_source(
                source_id,
                {
                    "status": "processing",
                },
            )

            content = self.storage.download(source["storage_path"])
            parsed_document = parse_source_content(
                mime_type=source.get("mime_type", ""),
                filename=source.get("filename", ""),
                content=content,
            )
            context.parsed_documents[source_id] = parsed_document

            existing_metadata = source.get("source_metadata") or {}
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}

            updated_metadata = {
                **existing_metadata,
                "parse": {
                    **parsed_document.to_parse_metadata(),
                    "parsed_at": utc_now_iso(),
                },
            }

            self.db.update_source(
                source_id,
                {
                    "source_metadata": updated_metadata,
                },
            )
            source["source_metadata"] = updated_metadata

        return mark_step(pipeline, "parse", status="completed")

    def run_source_research_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        skill_run_ids: list[str] = []

        for source in context.sources:
            source_id = source["id"]
            parsed_document = context.parsed_documents.get(source_id)

            if not parsed_document:
                raise RuntimeError(f"Parsed document missing for source {source_id}.")

            skill_run_id = self.source_research.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                parsed_document=parsed_document,
            )
            skill_run_ids.append(skill_run_id)

        detail = f"{len(skill_run_ids)} skill run(s)"
        last_skill_run_id = skill_run_ids[-1] if skill_run_ids else None

        return mark_step(
            pipeline,
            "source-research",
            status="completed",
            skill_run_id=last_skill_run_id,
            detail=detail,
        )

    def run_chunk_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        total_segments = 0

        for source in context.sources:
            source_id = source["id"]
            parsed_document = context.parsed_documents.get(source_id)

            if not parsed_document:
                raise RuntimeError(f"Parsed document missing for source {source_id}.")

            self.db.delete_ndr_segments_for_source(source_id)
            segment_rows = chunk_parsed_document(
                parsed_document=parsed_document,
                source_id=source_id,
                workspace_id=context.workspace_id,
            )
            self.db.insert_ndr_segments(segment_rows)
            total_segments += len(segment_rows)

            existing_metadata = source.get("source_metadata") or {}
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}

            parse_metadata = existing_metadata.get("parse", {})
            if not isinstance(parse_metadata, dict):
                parse_metadata = {}

            updated_metadata = {
                **existing_metadata,
                "parse": {
                    **parse_metadata,
                    "segment_count": len(segment_rows),
                    "chunked_at": utc_now_iso(),
                },
            }

            self.db.update_source(
                source_id,
                {
                    "status": "ready",
                    "source_metadata": updated_metadata,
                },
            )

        updated_pipeline = mark_step(
            pipeline,
            "chunk",
            status="completed",
            detail=f"{total_segments} segments",
        )
        return updated_pipeline, total_segments

    def run_document_deconstructor_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        skill_run_ids: list[str] = []

        for source in context.sources:
            skill_run_id = self.document_deconstructor.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
            )
            skill_run_ids.append(skill_run_id)

        detail = f"{len(skill_run_ids)} skill run(s)"
        last_skill_run_id = skill_run_ids[-1] if skill_run_ids else None

        return mark_step(
            pipeline,
            "document-deconstructor",
            status="completed",
            skill_run_id=last_skill_run_id,
            detail=detail,
        )

    def run_eleven_reader_script_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_mathesys_narration_step(
            context,
            pipeline,
            target_artifact="eleven_reader_script",
            step_name="eleven-reader-script",
            executor=self.eleven_reader_script,
        )

    def run_speechify_app_epub_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_mathesys_narration_step(
            context,
            pipeline,
            target_artifact="speechify_script",
            step_name="speechify-app-epub",
            executor=self.speechify_app_epub,
        )

    def run_speechify_api_ssml_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_mathesys_narration_step(
            context,
            pipeline,
            target_artifact="speechify_audio",
            step_name="speechify-api-ssml",
            executor=self.speechify_api_ssml,
        )

    def run_elevenlabs_structured_text_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_mathesys_narration_step(
            context,
            pipeline,
            target_artifact="elevenlabs_audio",
            step_name="elevenlabs-structured-text",
            executor=self.elevenlabs_structured_text,
        )

    def _run_mathesys_narration_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
        *,
        target_artifact: str,
        step_name: str,
        executor: Any,
    ) -> list[dict[str, Any]]:
        if target_artifact not in context.target_artifacts:
            return pipeline

        skill_run_ids: list[str] = []

        for source in context.sources:
            skill_run_id = executor.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
            )
            skill_run_ids.append(skill_run_id)

        detail = f"{len(skill_run_ids)} skill run(s)"
        last_skill_run_id = skill_run_ids[-1] if skill_run_ids else None

        return mark_step(
            pipeline,
            step_name,
            status="completed",
            skill_run_id=last_skill_run_id,
            detail=detail,
        )

    def run_flashcard_gen_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if "flashcards" not in context.target_artifacts:
            return pipeline

        return self._run_qngen_step(
            context,
            pipeline,
            step_name="flashcard-gen",
            executor=self.flashcard_gen,
        )

    def run_quiz_gen_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if "quizzes" not in context.target_artifacts:
            return pipeline

        return self._run_qngen_step(
            context,
            pipeline,
            step_name="quiz-gen",
            executor=self.quiz_gen,
        )

    def run_scenario_gen_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if "scenarios" not in context.target_artifacts:
            return pipeline

        return self._run_qngen_step(
            context,
            pipeline,
            step_name="scenario-gen",
            executor=self.scenario_gen,
        )

    def _run_qngen_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
        *,
        step_name: str,
        executor: Any,
    ) -> list[dict[str, Any]]:
        skill_run_ids: list[str] = []

        for source in context.sources:
            skill_run_id = executor.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
            )
            skill_run_ids.append(skill_run_id)

        detail = f"{len(skill_run_ids)} skill run(s)"
        last_skill_run_id = skill_run_ids[-1] if skill_run_ids else None

        return mark_step(
            pipeline,
            step_name,
            status="completed",
            skill_run_id=last_skill_run_id,
            detail=detail,
        )

    def execute(self, production_run_id: str) -> dict[str, Any]:
        production_run = self.db.get_production_run(production_run_id)

        if not production_run:
            raise RuntimeError(f"Production run not found: {production_run_id}")

        pipeline = copy.deepcopy(production_run.get("pipeline") or [])
        source_ids = production_run.get("source_ids") or []
        workspace_id = production_run["workspace_id"]

        sources = self.db.get_sources(source_ids)

        if len(sources) != len(source_ids):
            raise RuntimeError("One or more sources referenced by the production run no longer exist.")

        context = PipelineContext(
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            sources=sources,
            target_artifacts=production_run.get("target_artifacts") or [],
        )

        self.db.update_production_run(
            production_run_id,
            {
                "status": "running",
                "error": None,
            },
        )

        try:
            pipeline = self.run_store_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_parse_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_source_research_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline, segment_count = self.run_chunk_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_document_deconstructor_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_eleven_reader_script_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_speechify_app_epub_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_speechify_api_ssml_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_elevenlabs_structured_text_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_flashcard_gen_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_quiz_gen_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_scenario_gen_step(context, pipeline)
            self.db.update_production_run(
                production_run_id,
                {
                    "pipeline": pipeline,
                    "status": "completed",
                    "completed_at": utc_now_iso(),
                },
            )

            return {
                "production_run_id": production_run_id,
                "status": "completed",
                "message": "Production run completed.",
                "segment_count": segment_count,
            }
        except Exception as exc:
            logger.exception("Production run %s failed", production_run_id)
            self.db.update_production_run(
                production_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "pipeline": pipeline,
                    "completed_at": utc_now_iso(),
                },
            )

            for source in context.sources:
                if source.get("status") == "processing":
                    self.db.update_source(source["id"], {"status": "failed"})

            raise
