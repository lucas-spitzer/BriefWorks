from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.config import get_settings
from app.intellex.ingest import parse_artifact_path, structured_pages_artifact_path
from app.intellex.models import ParsedDocument
from app.intellex.stages.extract_chapter_knowledge import ExtractChapterKnowledgeStage
from app.intellex.stages.parse_document import ParseStage
from app.intellex.stages.promotion import merge_research_into_source_metadata
from app.intellex.stages.source_research import SourceResearchStage
from app.intellex.stages.wiki_promotion import promote_concepts_to_wiki, resolve_prerequisites
from app.intellex.source_readiness import source_intellex_complete
from app.intellex.wiki_slug import normalize_slug
from app.mathesys.stages.elevenlabs_structured_text import ElevenLabsStructuredTextStage
from app.mathesys.stages.speechify_api_ssml import SpeechifyApiSsmlStage
from app.qngen.assessment_promotion import (
    promote_flashcards,
    promote_quizzes,
    promote_scenarios,
)
from app.qngen.assessment_set_promotion import promote_assessment_set
from app.qngen.canonical_context import batch_concepts, build_source_concepts
from app.qngen.stages.assessment_set_gen import AssessmentSetGenStage
from app.qngen.stages.flashcard_gen import FlashcardGenStage
from app.qngen.stages.quiz_gen import QuizGenStage
from app.qngen.stages.scenario_gen import ScenarioGenStage
from app.qngen.validators import validate_assessment_items
from app.services.elevenlabs_client import ElevenLabsClient
from app.services.stage_run_billing import stage_run_completion_fields, tts_call_from_manifest
from app.services.speechify_client import SpeechifyClient
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage
from app.worker.structuring_executors import StructureStageExecutor

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SourceResearchStageExecutor:
    STAGE_ID = "source-research"
    STAGE_VERSION = "1.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        stage: SourceResearchStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.stage = stage or SourceResearchStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
        parsed_document: ParsedDocument,
    ) -> str:
        source_id = source["id"]
        stage_run = self.db.create_stage_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "stage_id": self.STAGE_ID,
                "stage_version": self.STAGE_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source_id,
                    "filename": source.get("filename"),
                    "mime_type": source.get("mime_type"),
                    "page_count": parsed_document.page_count,
                },
                "started_at": utc_now_iso(),
            },
        )
        stage_run_id = stage_run["id"]

        try:
            output, execution = self.stage.run(
                filename=str(source.get("filename") or ""),
                mime_type=str(source.get("mime_type") or ""),
                parsed_document=parsed_document,
            )
            researched_at = utc_now_iso()
            existing_metadata = source.get("source_metadata") or {}
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}

            updated_metadata = merge_research_into_source_metadata(
                existing_metadata,
                output,
                researched_at=researched_at,
            )

            self.db.update_source(
                source_id,
                {
                    "source_metadata": updated_metadata,
                },
            )
            source["source_metadata"] = updated_metadata

            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "completed",
                    "output": output.model_dump(),
                    "promoted": {
                        "source_ids": [source_id],
                        "metadata_namespace": "research",
                    },
                    **stage_run_completion_fields(execution),
                    "completed_at": utc_now_iso(),
                },
            )
            return stage_run_id
        except Exception as exc:
            logger.exception("Stage run %s failed", stage_run_id)
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


class ParseStageExecutor:
    STAGE_ID = "parse"
    STAGE_VERSION = "1.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        stage: ParseStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.stage = stage or ParseStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
        content: bytes,
    ) -> tuple[str, ParsedDocument, list[dict[str, Any]]]:
        source_id = source["id"]
        stage_run = self.db.create_stage_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "stage_id": self.STAGE_ID,
                "stage_version": self.STAGE_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source_id,
                    "filename": source.get("filename"),
                    "mime_type": source.get("mime_type"),
                    "file_size_bytes": len(content),
                },
                "started_at": utc_now_iso(),
            },
        )
        stage_run_id = stage_run["id"]

        try:
            output, execution = self.stage.run(
                mime_type=source.get("mime_type", ""),
                filename=source.get("filename", ""),
                content=content,
            )
            raw_markdown_path = parse_artifact_path(source["storage_path"])
            self.storage.upload(
                raw_markdown_path,
                output.raw_markdown.encode("utf-8"),
                bucket=self.storage.sources_bucket,
                content_type="text/markdown",
            )

            structured_path = structured_pages_artifact_path(source["storage_path"])
            self.storage.upload(
                structured_path,
                json.dumps({"pages": output.structured_pages}, ensure_ascii=False).encode("utf-8"),
                bucket=self.storage.sources_bucket,
                content_type="application/json",
            )

            existing_metadata = source.get("source_metadata") or {}
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}

            parse_metadata = {
                **output.document.to_parse_metadata(),
                "parsed_at": utc_now_iso(),
                "raw_markdown_path": raw_markdown_path,
                "structured_pages_path": structured_path,
                "structured_page_count": len(output.structured_pages),
            }
            updated_metadata = {
                **existing_metadata,
                "parse": parse_metadata,
            }

            self.db.update_source(
                source_id,
                {
                    "status": "processing",
                    "source_metadata": updated_metadata,
                },
            )
            source["source_metadata"] = updated_metadata

            stage_output = output.to_stage_output(raw_markdown_path=raw_markdown_path)
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "completed",
                    "output": stage_output,
                    "promoted": {
                        "source_ids": [source_id],
                        "metadata_namespace": "parse",
                    },
                    **stage_run_completion_fields(execution),
                    "completed_at": utc_now_iso(),
                },
            )
            return stage_run_id, output.document, output.structured_pages
        except Exception as exc:
            logger.exception("Stage run %s failed", stage_run_id)
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


class ExtractChapterKnowledgeStageExecutor:
    STAGE_ID = "extract-knowledge"
    STAGE_VERSION = "1.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        stage: ExtractChapterKnowledgeStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.stage = stage or ExtractChapterKnowledgeStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        source_id = source["id"]
        segments = self.db.list_ndr_segments_for_source(source_id)
        chapter_rows = self.db.list_document_chapters_for_source(source_id)

        if not segments:
            raise RuntimeError(f"No NDR segments found for source {source_id}.")
        if not chapter_rows:
            raise RuntimeError(f"No document chapters found for source {source_id}.")

        segment_index = {str(segment["id"]): segment for segment in segments}
        existing_entries = self.db.list_wiki_entries_for_workspace(workspace_id)
        existing_labels = [
            str(entry["preferred_label"])
            for entry in existing_entries
        ]

        stage_run = self.db.create_stage_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "stage_id": self.STAGE_ID,
                "stage_version": self.STAGE_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source_id,
                    "chapter_count": len(chapter_rows),
                    "segment_count": len(segments),
                },
                "started_at": utc_now_iso(),
            },
        )
        stage_run_id = stage_run["id"]

        try:
            source_metadata = source.get("source_metadata") or {}
            if not isinstance(source_metadata, dict):
                source_metadata = {}

            output, execution = self.stage.run(
                source_metadata=source_metadata,
                chapter_rows=chapter_rows,
                segments=segments,
                existing_labels=existing_labels,
            )

            inserts, updates, disputes = promote_concepts_to_wiki(
                workspace_id=workspace_id,
                source_id=source_id,
                stage_run_id=stage_run_id,
                stage_id=self.STAGE_ID,
                stage_version=self.STAGE_VERSION,
                concepts=output.items,
                segment_index=segment_index,
                existing_entries=existing_entries,
            )

            created_rows = self.db.insert_wiki_entries(inserts)

            for update in updates:
                wiki_id = update.pop("id")
                self.db.update_wiki_entry(wiki_id, update)

            if disputes:
                self.db.insert_wiki_disputes(disputes)

            all_rows = self.db.list_wiki_entries_for_workspace(workspace_id)
            slug_to_row = {str(row["canonical_slug"]): row for row in all_rows}

            for row in created_rows:
                slug_to_row[str(row["canonical_slug"])] = row

            prerequisite_updates = resolve_prerequisites(
                concepts=output.items,
                wiki_rows=list(slug_to_row.values()),
            )

            for update in prerequisite_updates:
                wiki_id = update.pop("id")
                self.db.update_wiki_entry(wiki_id, update)

            wiki_entry_ids = []
            for concept in output.items:
                slug = normalize_slug(concept.term_label)
                if slug in slug_to_row:
                    wiki_entry_ids.append(str(slug_to_row[slug]["id"]))
                    continue
                kind_slug = f"{slug}--{concept.entry_kind}"
                if kind_slug in slug_to_row:
                    wiki_entry_ids.append(str(slug_to_row[kind_slug]["id"]))

            item_counts = {
                "term": sum(1 for item in output.items if item.entry_kind == "term"),
                "concept": sum(1 for item in output.items if item.entry_kind == "concept"),
                "insight": sum(1 for item in output.items if item.entry_kind == "insight"),
            }

            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "completed",
                    "output": {
                        "chapters": [
                            {
                                "chapter_id": chapter.chapter_id,
                                "chapter_title": chapter.chapter_title,
                                "sequence_index": chapter.sequence_index,
                                "item_count": len(chapter.items),
                            }
                            for chapter in output.chapters
                        ],
                        "item_counts": item_counts,
                        "items": [item.model_dump() for item in output.items],
                    },
                    "promoted": {
                        "wiki_entry_ids": wiki_entry_ids,
                        "dispute_ids": [],
                        "disputes_logged": len(disputes),
                    },
                    **stage_run_completion_fields(execution),
                    "completed_at": utc_now_iso(),
                },
            )

            extracted_at = utc_now_iso()
            updated_metadata = {
                **source_metadata,
                "extract": {
                    "extracted_at": extracted_at,
                    "chapter_count": len(chapter_rows),
                    "item_counts": item_counts,
                },
            }
            self.db.update_source(
                source_id,
                {
                    "source_metadata": updated_metadata,
                },
            )
            source["source_metadata"] = updated_metadata

            return stage_run_id
        except Exception as exc:
            logger.exception("Stage run %s failed", stage_run_id)
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


def _serialize_narration_volume(volume: dict[str, Any]) -> tuple[bytes, str, str]:
    if "epub_bytes" in volume:
        return volume["epub_bytes"], "application/epub+zip", "epub"

    if "ssml" in volume:
        payload = str(volume["ssml"]).encode("utf-8")
        return payload, "application/ssml+xml", "ssml"

    if "structured_text" in volume:
        payload = json.dumps(volume["structured_text"], indent=2).encode("utf-8")
        return payload, "application/json", "json"

    raise RuntimeError("Narration volume is missing output bytes.")


def _run_mathesys_narration_stage(
    *,
    db: WorkerDatabase,
    storage: WorkerStorage,
    stage: Any,
    stage_id: str,
    stage_version: str,
    artifact_type: str,
    artifact_format: str,
    production_run_id: str,
    workspace_id: str,
    source: dict[str, Any],
    extra_manifest: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    synthesize_volume: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
    include_wiki: bool = True,
) -> str:
    source_id = source["id"]
    segments = db.list_ndr_segments_for_source(source_id)
    chapter_rows = db.list_document_chapters_for_source(source_id)

    if not segments:
        raise RuntimeError(f"No NDR segments found for source {source_id}.")

    wiki_entries: list[dict[str, Any]] = []

    if include_wiki:
        wiki_entries = [
            entry
            for entry in db.list_wiki_entries_for_workspace(workspace_id)
            if entry.get("status") == "canonical"
        ]

    stage_inputs: dict[str, Any] = {
        "source_id": source_id,
        "segment_count": len(segments),
    }

    if include_wiki:
        stage_inputs["wiki_entry_count"] = len(wiki_entries)
    else:
        stage_inputs["chapter_count"] = len(chapter_rows)

    stage_run = db.create_stage_run(
        {
            "production_run_id": production_run_id,
            "workspace_id": workspace_id,
            "stage_id": stage_id,
            "stage_version": stage_version,
            "module": "mathesys",
            "status": "running",
            "inputs": stage_inputs,
            "started_at": utc_now_iso(),
        },
    )
    stage_run_id = stage_run["id"]

    try:
        source_metadata = source.get("source_metadata") or {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}

        volumes, execution = stage.run(
            source_metadata=source_metadata,
            segments=segments,
            wiki_entries=wiki_entries,
            chapter_rows=chapter_rows,
        )

        artifact_ids: list[str] = []
        artifact_files: list[dict[str, Any]] = []
        tts_calls: list[dict[str, Any]] = []

        for volume in volumes:
            synthesized = synthesize_volume(volume) if synthesize_volume else None

            if synthesized is not None:
                file_bytes = synthesized["audio_bytes"]
                content_type = "audio/mpeg"
                extension = "mp3"
                resolved_format = "mp3"
            else:
                file_bytes, content_type, extension = _serialize_narration_volume(volume)
                resolved_format = artifact_format

            filename = f"{normalize_slug(volume['title'])}.{extension}"
            manifest = {
                "pages_approx": volume["pages_approx"],
                "part": volume["part"],
                "parts_total": volume["parts_total"],
                "wiki_ids_cited": execution["wiki_ids_cited"],
                "segment_ids_used": execution["segment_ids_used"],
                "transformations": execution["transformations"],
                "warnings": execution.get("warnings") or [],
                "validation": volume.get("validation"),
                "prepare": execution.get("prepare"),
            }

            if extra_manifest:
                manifest.update(extra_manifest(volume))

            if synthesized is not None:
                synthesized_manifest = synthesized.get("manifest") or {}
                manifest.update(synthesized_manifest)
                tts_call = tts_call_from_manifest(synthesized_manifest)

                if tts_call is not None:
                    tts_calls.append(tts_call)

            artifact_row = db.create_artifact(
                {
                    "workspace_id": workspace_id,
                    "source_id": source_id,
                    "production_run_id": production_run_id,
                    "artifact_type": artifact_type,
                    "format": resolved_format,
                    "filename": filename,
                    "storage_path": "pending",
                    "file_size_bytes": 0,
                    "manifest": manifest,
                    "origin": {
                        "stage_run_id": stage_run_id,
                        "stage_id": stage_id,
                        "stage_version": stage_version,
                    },
                },
            )
            artifact_id = artifact_row["id"]
            storage_path = f"workspaces/{workspace_id}/artifacts/{artifact_id}/{filename}"

            storage.upload(storage_path, file_bytes, content_type=content_type)

            db.update_artifact(
                artifact_id,
                {
                    "storage_path": storage_path,
                    "file_size_bytes": len(file_bytes),
                },
            )

            artifact_ids.append(artifact_id)
            artifact_files.append(
                {
                    "artifact_id": artifact_id,
                    "filename": filename,
                    "storage_path": storage_path,
                    "pages_approx": volume["pages_approx"],
                    "part": volume["part"],
                    "parts_total": volume["parts_total"],
                },
            )

        db.update_stage_run(
            stage_run_id,
            {
                "status": "completed",
                "output": {
                    "files": artifact_files,
                    "wiki_ids_cited": execution["wiki_ids_cited"],
                    "segment_ids_used": execution["segment_ids_used"],
                    "transformations": execution["transformations"],
                    "warnings": execution.get("warnings") or [],
                },
                "promoted": {
                    "artifact_ids": artifact_ids,
                },
                **stage_run_completion_fields(execution, extra_calls=tts_calls or None),
                "completed_at": utc_now_iso(),
            },
        )
        return stage_run_id
    except Exception as exc:
        logger.exception("Stage run %s failed", stage_run_id)
        db.update_stage_run(
            stage_run_id,
            {
                "status": "failed",
                "error": str(exc),
                "completed_at": utc_now_iso(),
            },
        )
        raise


class SpeechifyApiSsmlStageExecutor:
    STAGE_ID = "speechify-audio"
    STAGE_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        stage: SpeechifyApiSsmlStage | None = None,
        client: SpeechifyClient | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.stage = stage or SpeechifyApiSsmlStage()
        self.client = client or SpeechifyClient()

    def _synthesize_volume(self, volume: dict[str, Any]) -> dict[str, Any] | None:
        # Speechify MP3 synthesis is gated behind the API key. Without it we
        # store the .ssml artifact and flag that audio is pending.
        if not self.client.enabled:
            return None

        ssml = str(volume.get("ssml") or "").strip()

        if not ssml:
            return None

        result = self.client.synthesize_ssml(ssml)

        return {
            "audio_bytes": result["audio_bytes"],
            "manifest": {
                "voice_id": result["voice_id"],
                "model": result["model"],
                "character_count": result["character_count"],
            },
        }

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        audio_pending = not self.client.enabled

        return _run_mathesys_narration_stage(
            db=self.db,
            storage=self.storage,
            stage=self.stage,
            stage_id=self.STAGE_ID,
            stage_version=self.STAGE_VERSION,
            artifact_type="speechify_audio",
            artifact_format="ssml",
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            extra_manifest=lambda volume: {
                "section_count": volume.get("section_count"),
                "estimated_character_count": volume.get("estimated_character_count"),
                **(
                    {"audio_note": "MP3 pending Speechify API key"}
                    if audio_pending
                    else {}
                ),
            },
            synthesize_volume=self._synthesize_volume,
        )


class ElevenLabsStructuredTextStageExecutor:
    STAGE_ID = "elevenlabs-audio"
    STAGE_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        stage: ElevenLabsStructuredTextStage | None = None,
        client: ElevenLabsClient | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.stage = stage or ElevenLabsStructuredTextStage()
        self.client = client or ElevenLabsClient()

    def _synthesize_volume(self, volume: dict[str, Any]) -> dict[str, Any] | None:
        # Without an API key we keep the structured-text JSON artifact so the
        # run still succeeds; the audio can be regenerated once a key is set.
        if not self.client.enabled:
            return None

        text = str((volume.get("structured_text") or {}).get("text") or "").strip()

        if not text:
            return None

        result = self.client.synthesize_long_text(text)

        return {
            "audio_bytes": result["audio_bytes"],
            "manifest": {
                "voice_id": result["voice_id"],
                "model_id": result["model_id"],
                "character_count": result["character_count"],
                "tts_request_count": result["request_count"],
            },
        }

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_mathesys_narration_stage(
            db=self.db,
            storage=self.storage,
            stage=self.stage,
            stage_id=self.STAGE_ID,
            stage_version=self.STAGE_VERSION,
            artifact_type="elevenlabs_audio",
            artifact_format="elevenlabs_json",
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            extra_manifest=lambda volume: {
                "model_id": (volume.get("structured_text") or {}).get("model_id"),
            },
            synthesize_volume=self._synthesize_volume,
        )


class FlashcardGenStageExecutor:
    STAGE_ID = "generate-flashcards"
    STAGE_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        stage: FlashcardGenStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.stage = stage or FlashcardGenStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_qngen_stage(
            db=self.db,
            stage=self.stage,
            stage_id=self.STAGE_ID,
            stage_version=self.STAGE_VERSION,
            module=self.MODULE,
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            promote_items=lambda **kwargs: promote_flashcards(
                flashcards=kwargs["items"],
                workspace_id=kwargs["workspace_id"],
                source_id=kwargs["source_id"],
                production_run_id=kwargs["production_run_id"],
                stage_run_id=kwargs["stage_run_id"],
                stage_id=kwargs["stage_id"],
                stage_version=kwargs["stage_version"],
            ),
            insert_rows=self.db.insert_flashcards,
            output_key="flashcards",
            promoted_key="flashcard_ids",
        )


class QuizGenStageExecutor:
    STAGE_ID = "generate-questions"
    STAGE_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        stage: QuizGenStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.stage = stage or QuizGenStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_qngen_stage(
            db=self.db,
            stage=self.stage,
            stage_id=self.STAGE_ID,
            stage_version=self.STAGE_VERSION,
            module=self.MODULE,
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            promote_items=lambda **kwargs: promote_quizzes(
                questions=kwargs["items"],
                workspace_id=kwargs["workspace_id"],
                source_id=kwargs["source_id"],
                production_run_id=kwargs["production_run_id"],
                stage_run_id=kwargs["stage_run_id"],
                stage_id=kwargs["stage_id"],
                stage_version=kwargs["stage_version"],
            ),
            insert_rows=self.db.insert_quizzes,
            output_key="questions",
            promoted_key="quiz_ids",
        )


class ScenarioGenStageExecutor:
    STAGE_ID = "generate-scenarios"
    STAGE_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        stage: ScenarioGenStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.stage = stage or ScenarioGenStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_qngen_stage(
            db=self.db,
            stage=self.stage,
            stage_id=self.STAGE_ID,
            stage_version=self.STAGE_VERSION,
            module=self.MODULE,
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            promote_items=lambda **kwargs: promote_scenarios(
                scenarios=kwargs["items"],
                workspace_id=kwargs["workspace_id"],
                source_id=kwargs["source_id"],
                production_run_id=kwargs["production_run_id"],
                stage_run_id=kwargs["stage_run_id"],
                stage_id=kwargs["stage_id"],
                stage_version=kwargs["stage_version"],
            ),
            insert_rows=self.db.insert_scenarios,
            output_key="scenarios",
            promoted_key="scenario_ids",
        )


class AssessmentSetGenStageExecutor:
    STAGE_ID = "assessment-set-gen"
    STAGE_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        stage: AssessmentSetGenStage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.stage = stage or AssessmentSetGenStage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
        assessment_types: list[str],
    ) -> str:
        source_id = source["id"]
        segments = self.db.list_ndr_segments_for_source(source_id)

        if not segments:
            raise RuntimeError(f"No NDR segments found for source {source_id}.")

        has_structure_stage_run = self.db.has_completed_stage_run_for_source(
            source_id,
            StructureStageExecutor.STAGE_ID,
        )
        has_extract_stage_run = self.db.has_completed_stage_run_for_source(
            source_id,
            ExtractChapterKnowledgeStageExecutor.STAGE_ID,
        )
        has_document_chapters = self.db.has_document_chapters_for_source(source_id)
        if not source_intellex_complete(
            source,
            has_segments=True,
            has_document_chapters=has_document_chapters,
            has_structure_stage_run=has_structure_stage_run,
            has_extract_stage_run=has_extract_stage_run,
        ):
            raise RuntimeError(
                f"Source {source_id} is not intellex-complete. "
                "Run parse through extract-knowledge before generating assessments.",
            )

        wiki_entries = self.db.list_wiki_entries_for_workspace(workspace_id)
        concepts = build_source_concepts(
            wiki_entries=wiki_entries,
            source_id=source_id,
            segments=segments,
        )

        if not concepts:
            raise RuntimeError(
                f"No canonical wiki concepts with evidence found for source {source_id}. "
                "Run extract-knowledge first.",
            )

        settings = get_settings()
        concept_batches = batch_concepts(
            concepts,
            batch_size=settings.qngen_concept_batch_size,
        )
        wiki_ids = {concept.wiki_id for concept in concepts}
        segment_ids = {str(segment["id"]) for segment in segments}

        stage_run = self.db.create_stage_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "stage_id": self.STAGE_ID,
                "stage_version": self.STAGE_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source_id,
                    "segment_count": len(segments),
                    "concept_count": len(concepts),
                    "assessment_types": assessment_types,
                },
                "started_at": utc_now_iso(),
            },
        )
        stage_run_id = stage_run["id"]

        try:
            source_metadata = source.get("source_metadata") or {}
            if not isinstance(source_metadata, dict):
                source_metadata = {}

            output, execution = self.stage.run(
                source_metadata=source_metadata,
                concept_batches=concept_batches,
                assessment_types=assessment_types,
            )
            validated_items, validation_report = validate_assessment_items(
                items=output.items,
                concepts=concepts,
                segment_ids=segment_ids,
                wiki_ids=wiki_ids,
            )

            assessment_set_id = str(uuid.uuid4())
            set_row, flashcard_rows, quiz_rows, scenario_rows = promote_assessment_set(
                workspace_id=workspace_id,
                source_id=source_id,
                production_run_id=production_run_id,
                stage_run_id=stage_run_id,
                stage_id=self.STAGE_ID,
                stage_version=self.STAGE_VERSION,
                source_metadata=source_metadata,
                assessment_types=assessment_types,
                items=validated_items,
                assessment_set_id=assessment_set_id,
            )

            created_set = self.db.insert_assessment_set(set_row)
            created_flashcards = self.db.insert_flashcards(flashcard_rows)
            created_quizzes = self.db.insert_quizzes(quiz_rows)
            created_scenarios = self.db.insert_scenarios(scenario_rows)

            output_data = {
                "items": validated_items,
                "validation_report": validation_report,
                "assessment_set_id": created_set["id"],
            }

            db_update = {
                "status": "completed",
                "output": output_data,
                "promoted": {
                    "assessment_set_id": created_set["id"],
                    "flashcard_ids": [str(row["id"]) for row in created_flashcards],
                    "quiz_ids": [str(row["id"]) for row in created_quizzes],
                    "scenario_ids": [str(row["id"]) for row in created_scenarios],
                },
                **stage_run_completion_fields(execution),
                "completed_at": utc_now_iso(),
            }
            self.db.update_stage_run(stage_run_id, db_update)
            return stage_run_id
        except Exception as exc:
            logger.exception("Stage run %s failed", stage_run_id)
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


def _run_qngen_stage(
    *,
    db: WorkerDatabase,
    stage: Any,
    stage_id: str,
    stage_version: str,
    module: str,
    production_run_id: str,
    workspace_id: str,
    source: dict[str, Any],
    promote_items: Any,
    insert_rows: Any,
    output_key: str,
    promoted_key: str,
) -> str:
    source_id = source["id"]
    segments = db.list_ndr_segments_for_source(source_id)

    if not segments:
        raise RuntimeError(f"No NDR segments found for source {source_id}.")

    wiki_entries = db.list_wiki_entries_for_workspace(workspace_id)

    stage_run = db.create_stage_run(
        {
            "production_run_id": production_run_id,
            "workspace_id": workspace_id,
            "stage_id": stage_id,
            "stage_version": stage_version,
            "module": module,
            "status": "running",
            "inputs": {
                "source_id": source_id,
                "segment_count": len(segments),
                "wiki_entry_count": len(
                    [entry for entry in wiki_entries if entry.get("status") == "canonical"],
                ),
            },
            "started_at": utc_now_iso(),
        },
    )
    stage_run_id = stage_run["id"]

    try:
        source_metadata = source.get("source_metadata") or {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}

        output, execution = stage.run(
            source_metadata=source_metadata,
            segments=segments,
            wiki_entries=wiki_entries,
        )
        output_data = output.model_dump()
        items = output_data[output_key]

        rows = promote_items(
            items=items,
            workspace_id=workspace_id,
            source_id=source_id,
            production_run_id=production_run_id,
            stage_run_id=stage_run_id,
            stage_id=stage_id,
            stage_version=stage_version,
        )
        created_rows = insert_rows(rows)
        promoted_ids = [str(row["id"]) for row in created_rows]

        db.update_stage_run(
            stage_run_id,
            {
                "status": "completed",
                "output": output_data,
                "promoted": {promoted_key: promoted_ids},
                **stage_run_completion_fields(execution),
                "completed_at": utc_now_iso(),
            },
        )
        return stage_run_id
    except Exception as exc:
        logger.exception("Stage run %s failed", stage_run_id)
        db.update_stage_run(
            stage_run_id,
            {
                "status": "failed",
                "error": str(exc),
                "completed_at": utc_now_iso(),
            },
        )
        raise
