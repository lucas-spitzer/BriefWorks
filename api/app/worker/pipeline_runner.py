from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.intellex.models import ParsedDocument
from app.intellex.source_readiness import source_intellex_complete
from app.intellex.structuring.chunk import build_segments_and_chapters
from app.intellex.structuring.models import Book, Element
from app.worker.db import WorkerDatabase
from app.worker.stage_executor import (
    ElevenLabsStructuredTextStageExecutor,
    ExtractChapterKnowledgeStageExecutor,
    FlashcardGenStageExecutor,
    ParseStageExecutor,
    QuizGenStageExecutor,
    ScenarioGenStageExecutor,
    SourceResearchStageExecutor,
    SpeechifyApiSsmlStageExecutor,
)
from app.worker.storage import WorkerStorage
from app.worker.structuring_executors import (
    CreateEbookStageExecutor,
    NormalizeStageExecutor,
    PdfStructureValidationStageExecutor,
    StructureStageExecutor,
    TrimBoundariesStageExecutor,
)

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def mark_step(
    pipeline: list[dict[str, Any]],
    step_name: str,
    *,
    status: str,
    stage_run_id: str | None = None,
    detail: str | None = None,
) -> list[dict[str, Any]]:
    updated_pipeline: list[dict[str, Any]] = []

    for step in pipeline:
        next_step = copy.deepcopy(step)

        if next_step.get("step") == step_name:
            next_step["status"] = status

            if stage_run_id:
                next_step["stage_run_id"] = stage_run_id

            if detail:
                next_step["detail"] = detail

        updated_pipeline.append(next_step)

    return updated_pipeline


def step_detail(*, processed: int, reused: int, suffix: str | None = None) -> str:
    parts: list[str] = []

    if processed:
        parts.append(f"{processed} processed")

    if reused:
        parts.append(f"{reused} reused")

    detail = ", ".join(parts) if parts else "0 sources"

    if suffix:
        return f"{detail}; {suffix}"

    return detail


@dataclass
class PipelineContext:
    production_run_id: str
    workspace_id: str
    sources: list[dict[str, Any]]
    parsed_documents: dict[str, ParsedDocument] = field(default_factory=dict)
    structured_pages: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    normalized_elements: dict[str, list[Element]] = field(default_factory=dict)
    trimmed_elements: dict[str, list[Element]] = field(default_factory=dict)
    books: dict[str, Book] = field(default_factory=dict)
    target_artifacts: list[str] = field(default_factory=list)
    intellex_complete_source_ids: set[str] = field(default_factory=set)


class PipelineRunner:
    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        source_research: SourceResearchStageExecutor | None = None,
        parse: ParseStageExecutor | None = None,
        normalize: NormalizeStageExecutor | None = None,
        trim: TrimBoundariesStageExecutor | None = None,
        structure: StructureStageExecutor | None = None,
        validate: PdfStructureValidationStageExecutor | None = None,
        extract_chapter_knowledge: ExtractChapterKnowledgeStageExecutor | None = None,
        create_ebook: CreateEbookStageExecutor | None = None,
        speechify_api_ssml: SpeechifyApiSsmlStageExecutor | None = None,
        elevenlabs_structured_text: ElevenLabsStructuredTextStageExecutor | None = None,
        flashcard_gen: FlashcardGenStageExecutor | None = None,
        quiz_gen: QuizGenStageExecutor | None = None,
        scenario_gen: ScenarioGenStageExecutor | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.source_research = source_research or SourceResearchStageExecutor(self.db)
        self.parse = parse or ParseStageExecutor(self.db, self.storage)
        self.normalize = normalize or NormalizeStageExecutor(self.db, self.storage)
        self.trim = trim or TrimBoundariesStageExecutor(self.db, self.storage)
        self.structure = structure or StructureStageExecutor(self.db, self.storage)
        self.validate = validate or PdfStructureValidationStageExecutor(self.db, self.storage)
        self.extract_chapter_knowledge = (
            extract_chapter_knowledge or ExtractChapterKnowledgeStageExecutor(self.db)
        )
        self.create_ebook = create_ebook or CreateEbookStageExecutor(self.db, self.storage)
        self.speechify_api_ssml = speechify_api_ssml or SpeechifyApiSsmlStageExecutor(
            self.db,
            self.storage,
        )
        self.elevenlabs_structured_text = (
            elevenlabs_structured_text
            or ElevenLabsStructuredTextStageExecutor(self.db, self.storage)
        )
        self.flashcard_gen = flashcard_gen or FlashcardGenStageExecutor(self.db)
        self.quiz_gen = quiz_gen or QuizGenStageExecutor(self.db)
        self.scenario_gen = scenario_gen or ScenarioGenStageExecutor(self.db)

    def run_store_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unstored = [
            source["id"]
            for source in context.sources
            if not source.get("storage_path")
        ]

        if unstored:
            raise RuntimeError(f"Sources missing storage paths: {', '.join(unstored)}")

        reused = len(context.intellex_complete_source_ids)
        processed = len(context.sources) - reused

        return mark_step(
            pipeline,
            "store",
            status="completed",
            detail=step_detail(processed=processed, reused=reused),
        )

    def run_parse_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        stage_run_ids: list[str] = []
        total_pages = 0
        reused = 0

        for source in context.sources:
            source_id = source["id"]

            if source_id in context.intellex_complete_source_ids:
                parse_metadata = (source.get("source_metadata") or {}).get("parse")
                if isinstance(parse_metadata, dict):
                    page_count = parse_metadata.get("page_count")
                    if isinstance(page_count, int):
                        total_pages += page_count
                reused += 1
                continue

            content = self.storage.download(source["storage_path"])
            stage_run_id, parsed_document, structured_pages = self.parse.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                content=content,
            )
            context.parsed_documents[source_id] = parsed_document
            context.structured_pages[source_id] = structured_pages
            stage_run_ids.append(stage_run_id)
            total_pages += parsed_document.page_count

        processed = len(context.sources) - reused
        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None

        return mark_step(
            pipeline,
            "parse",
            status="completed",
            stage_run_id=last_stage_run_id,
            detail=step_detail(
                processed=processed,
                reused=reused,
                suffix=f"{total_pages} pages",
            ),
        )

    def _run_structuring_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
        *,
        step_name: str,
        run_source: Any,
    ) -> list[dict[str, Any]]:
        stage_run_ids: list[str] = []
        reused = 0

        for source in context.sources:
            source_id = source["id"]
            if source_id in context.intellex_complete_source_ids:
                reused += 1
                continue
            stage_run_ids.append(run_source(source))

        processed = len(context.sources) - reused
        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None

        return mark_step(
            pipeline,
            step_name,
            status="completed",
            stage_run_id=last_stage_run_id,
            detail=step_detail(
                processed=processed,
                reused=reused,
                suffix=f"{len(stage_run_ids)} stage run(s)" if stage_run_ids else None,
            ),
        )

    def run_normalize_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def run_source(source: dict[str, Any]) -> str:
            source_id = source["id"]
            structured_pages = context.structured_pages.get(source_id)
            if not structured_pages:
                raise RuntimeError(
                    f"No structured layout for source {source_id}. The parse step must capture "
                    "LlamaParse `items` (agentic layout) for the structuring stages."
                )
            stage_run_id, elements = self.normalize.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                structured_pages=structured_pages,
            )
            context.normalized_elements[source_id] = elements
            return stage_run_id

        return self._run_structuring_step(
            context, pipeline, step_name="normalize-document", run_source=run_source
        )

    def run_trim_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def run_source(source: dict[str, Any]) -> str:
            source_id = source["id"]
            elements = context.normalized_elements.get(source_id)
            if elements is None:
                raise RuntimeError(f"Normalized elements missing for source {source_id}.")
            stage_run_id, trimmed = self.trim.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                elements=elements,
            )
            context.trimmed_elements[source_id] = trimmed
            return stage_run_id

        return self._run_structuring_step(
            context, pipeline, step_name="trim-document-boundaries", run_source=run_source
        )

    def run_structure_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def run_source(source: dict[str, Any]) -> str:
            source_id = source["id"]
            trimmed = context.trimmed_elements.get(source_id)
            if trimmed is None:
                raise RuntimeError(f"Trimmed elements missing for source {source_id}.")
            stage_run_id, book = self.structure.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                trimmed_elements=trimmed,
            )
            context.books[source_id] = book
            return stage_run_id

        return self._run_structuring_step(
            context, pipeline, step_name="structure-document", run_source=run_source
        )

    def run_validate_step(self, context: PipelineContext, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def run_source(source: dict[str, Any]) -> str:
            source_id = source["id"]
            book = context.books.get(source_id)
            if book is None:
                raise RuntimeError(f"Structured book missing for source {source_id}.")
            return self.validate.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                book=book,
            )

        return self._run_structuring_step(
            context, pipeline, step_name="validate-structure", run_source=run_source
        )

    def run_chunk_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        total_segments = 0
        reused = 0

        for source in context.sources:
            source_id = source["id"]

            if source_id in context.intellex_complete_source_ids:
                total_segments += len(self.db.list_ndr_segments_for_source(source_id))
                reused += 1
                continue

            book = context.books.get(source_id)
            if book is None:
                raise RuntimeError(f"Structured book missing for source {source_id}.")

            segment_rows, chapter_rows = build_segments_and_chapters(
                book,
                source_id=source_id,
                workspace_id=context.workspace_id,
            )

            self.db.delete_ndr_segments_for_source(source_id)
            self.db.insert_ndr_segments(segment_rows)
            self.db.delete_document_chapters_for_source(source_id)
            self.db.insert_document_chapters(chapter_rows)
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
                    "chapter_count": len(chapter_rows),
                    "chunked_at": utc_now_iso(),
                },
            }
            self.db.update_source(
                source_id,
                {"status": "ready", "source_metadata": updated_metadata},
            )
            source["source_metadata"] = updated_metadata

        processed = len(context.sources) - reused

        updated_pipeline = mark_step(
            pipeline,
            "chunk",
            status="completed",
            detail=step_detail(
                processed=processed,
                reused=reused,
                suffix=f"{total_segments} segments",
            ),
        )
        return updated_pipeline, total_segments

    def run_source_research_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        stage_run_ids: list[str] = []
        reused = 0

        for source in context.sources:
            source_id = source["id"]

            if source_id in context.intellex_complete_source_ids:
                reused += 1
                continue

            parsed_document = context.parsed_documents.get(source_id)
            if not parsed_document:
                raise RuntimeError(f"Parsed document missing for source {source_id}.")

            stage_run_id = self.source_research.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
                parsed_document=parsed_document,
            )
            stage_run_ids.append(stage_run_id)

        processed = len(context.sources) - reused
        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None

        return mark_step(
            pipeline,
            "source-research",
            status="completed",
            stage_run_id=last_stage_run_id,
            detail=step_detail(
                processed=processed,
                reused=reused,
                suffix=f"{len(stage_run_ids)} stage run(s)" if stage_run_ids else None,
            ),
        )

    def run_extract_chapter_knowledge_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        stage_run_ids: list[str] = []
        reused = 0

        for source in context.sources:
            source_id = source["id"]

            if source_id in context.intellex_complete_source_ids:
                reused += 1
                continue

            stage_run_id = self.extract_chapter_knowledge.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
            )
            stage_run_ids.append(stage_run_id)

        processed = len(context.sources) - reused
        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None

        return mark_step(
            pipeline,
            "extract-knowledge",
            status="completed",
            stage_run_id=last_stage_run_id,
            detail=step_detail(
                processed=processed,
                reused=reused,
                suffix=f"{len(stage_run_ids)} stage run(s)" if stage_run_ids else None,
            ),
        )

    def run_create_ebook_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if "eleven_reader_script" not in context.target_artifacts:
            return pipeline

        stage_run_ids: list[str] = []
        for source in context.sources:
            stage_run_ids.append(
                self.create_ebook.run_for_source(
                    production_run_id=context.production_run_id,
                    workspace_id=context.workspace_id,
                    source=source,
                )
            )

        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None
        return mark_step(
            pipeline,
            "create-ebook",
            status="completed",
            stage_run_id=last_stage_run_id,
            detail=f"{len(stage_run_ids)} stage run(s)",
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
            step_name="speechify-audio",
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
            step_name="elevenlabs-audio",
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

        stage_run_ids: list[str] = []

        for source in context.sources:
            stage_run_id = executor.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
            )
            stage_run_ids.append(stage_run_id)

        detail = f"{len(stage_run_ids)} stage run(s)"
        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None

        return mark_step(
            pipeline,
            step_name,
            status="completed",
            stage_run_id=last_stage_run_id,
            detail=detail,
        )

    def run_generate_flashcards_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_qngen_step(
            context,
            pipeline,
            target_artifact="flashcards",
            step_name="generate-flashcards",
            executor=self.flashcard_gen,
        )

    def run_generate_questions_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_qngen_step(
            context,
            pipeline,
            target_artifact="quizzes",
            step_name="generate-questions",
            executor=self.quiz_gen,
        )

    def run_generate_scenarios_step(
        self,
        context: PipelineContext,
        pipeline: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._run_qngen_step(
            context,
            pipeline,
            target_artifact="scenarios",
            step_name="generate-scenarios",
            executor=self.scenario_gen,
        )

    def _run_qngen_step(
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

        stage_run_ids: list[str] = []

        for source in context.sources:
            stage_run_id = executor.run_for_source(
                production_run_id=context.production_run_id,
                workspace_id=context.workspace_id,
                source=source,
            )
            stage_run_ids.append(stage_run_id)

        detail = f"{len(stage_run_ids)} stage run(s)"
        last_stage_run_id = stage_run_ids[-1] if stage_run_ids else None

        return mark_step(
            pipeline,
            step_name,
            status="completed",
            stage_run_id=last_stage_run_id,
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

        for source in sources:
            source_id = source["id"]
            has_segments = bool(self.db.list_ndr_segments_for_source(source_id))
            has_document_chapters = self.db.has_document_chapters_for_source(source_id)
            has_structure_stage_run = self.db.has_completed_stage_run_for_source(
                source_id,
                StructureStageExecutor.STAGE_ID,
            )
            has_extract_stage_run = self.db.has_completed_stage_run_for_source(
                source_id,
                ExtractChapterKnowledgeStageExecutor.STAGE_ID,
            )

            if source_intellex_complete(
                source,
                has_segments=has_segments,
                has_document_chapters=has_document_chapters,
                has_structure_stage_run=has_structure_stage_run,
                has_extract_stage_run=has_extract_stage_run,
            ):
                context.intellex_complete_source_ids.add(source_id)

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

            pipeline = self.run_normalize_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_trim_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_structure_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_validate_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline, segment_count = self.run_chunk_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_source_research_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_extract_chapter_knowledge_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_create_ebook_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_speechify_api_ssml_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_elevenlabs_structured_text_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_generate_flashcards_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_generate_questions_step(context, pipeline)
            self.db.update_production_run(production_run_id, {"pipeline": pipeline})

            pipeline = self.run_generate_scenarios_step(context, pipeline)
            cost_usd = self.db.sum_stage_run_costs(production_run_id)
            self.db.update_production_run(
                production_run_id,
                {
                    "pipeline": pipeline,
                    "status": "completed",
                    "completed_at": utc_now_iso(),
                    "cost_usd": cost_usd,
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
            cost_usd = self.db.sum_stage_run_costs(production_run_id)
            self.db.update_production_run(
                production_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "pipeline": pipeline,
                    "completed_at": utc_now_iso(),
                    "cost_usd": cost_usd,
                },
            )

            for source in context.sources:
                if source.get("status") == "processing":
                    self.db.update_source(source["id"], {"status": "failed"})

            raise
