from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.config import get_settings
from app.intellex.models import ParsedDocument
from app.intellex.skills.document_deconstructor import DocumentDeconstructorSkill
from app.intellex.skills.extract_chapter_knowledge import ExtractChapterKnowledgeSkill
from app.intellex.skills.prepare import PrepareSkill, summarize_prepare_reasons
from app.intellex.skills.promotion import merge_research_into_source_metadata
from app.intellex.skills.source_research import SourceResearchSkill
from app.intellex.skills.wiki_promotion import promote_concepts_to_wiki, resolve_prerequisites
from app.intellex.source_readiness import source_intellex_complete
from app.intellex.wiki_slug import normalize_slug
from app.mathesys.skills.eleven_reader_script import ElevenReaderScriptSkill
from app.mathesys.skills.elevenlabs_structured_text import ElevenLabsStructuredTextSkill
from app.mathesys.skills.speechify_api_ssml import SpeechifyApiSsmlSkill
from app.qngen.assessment_promotion import (
    promote_flashcards,
    promote_quizzes,
    promote_scenarios,
)
from app.qngen.assessment_set_promotion import promote_assessment_set
from app.qngen.canonical_context import batch_concepts, build_source_concepts
from app.qngen.skills.assessment_set_gen import AssessmentSetGenSkill
from app.qngen.skills.flashcard_gen import FlashcardGenSkill
from app.qngen.skills.quiz_gen import QuizGenSkill
from app.qngen.skills.scenario_gen import ScenarioGenSkill
from app.qngen.validators import validate_assessment_items
from app.services.elevenlabs_client import ElevenLabsClient
from app.services.skill_run_billing import skill_run_completion_fields, tts_call_from_manifest
from app.services.speechify_client import SpeechifyClient
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SourceResearchSkillExecutor:
    SKILL_ID = "source-research"
    SKILL_VERSION = "1.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: SourceResearchSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or SourceResearchSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
        parsed_document: ParsedDocument,
    ) -> str:
        source_id = source["id"]
        skill_run = self.db.create_skill_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "skill_id": self.SKILL_ID,
                "skill_version": self.SKILL_VERSION,
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
        skill_run_id = skill_run["id"]

        try:
            output, execution = self.skill.run(
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

            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "completed",
                    "output": output.model_dump(),
                    "promoted": {
                        "source_ids": [source_id],
                        "metadata_namespace": "research",
                    },
                    **skill_run_completion_fields(execution),
                    "completed_at": utc_now_iso(),
                },
            )
            return skill_run_id
        except Exception as exc:
            logger.exception("Skill run %s failed", skill_run_id)
            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


class PrepareSkillExecutor:
    SKILL_ID = "prepare-document"
    SKILL_VERSION = "2.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: PrepareSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or PrepareSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
        parsed_document: ParsedDocument,
    ) -> tuple[str, ParsedDocument]:
        source_id = source["id"]
        skill_run = self.db.create_skill_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "skill_id": self.SKILL_ID,
                "skill_version": self.SKILL_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source_id,
                    "line_count": len(parsed_document.lines),
                    "page_count": parsed_document.page_count,
                },
                "started_at": utc_now_iso(),
            },
        )
        skill_run_id = skill_run["id"]

        try:
            output, execution = self.skill.run(parsed_document=parsed_document)
            prepared_at = utc_now_iso()
            existing_metadata = source.get("source_metadata") or {}
            if not isinstance(existing_metadata, dict):
                existing_metadata = {}

            prepare_metadata = {
                "prepared_at": prepared_at,
                "kept_line_count": output.kept_line_count,
                "excluded_line_count": output.excluded_line_count,
                "excluded_pages": output.excluded_pages,
                "reasons_summary": summarize_prepare_reasons(output.reasons),
                "pre_filter": output.pre_filter_report,
                "validation": output.validation_report,
            }

            updated_metadata = {
                **existing_metadata,
                "prepare": prepare_metadata,
            }

            self.db.update_source(
                source_id,
                {
                    "source_metadata": updated_metadata,
                },
            )
            source["source_metadata"] = updated_metadata

            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "completed",
                    "output": {
                        "excluded_line_ids": output.excluded_line_ids,
                        "excluded_pages": output.excluded_pages,
                        "reasons": output.reasons,
                        "kept_line_count": output.kept_line_count,
                        "excluded_line_count": output.excluded_line_count,
                    },
                    "promoted": {
                        "source_ids": [source_id],
                        "metadata_namespace": "prepare",
                    },
                    **skill_run_completion_fields(execution),
                    "completed_at": utc_now_iso(),
                },
            )
            return skill_run_id, output.prepared_document
        except Exception as exc:
            logger.exception("Skill run %s failed", skill_run_id)
            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


class DocumentDeconstructorSkillExecutor:
    SKILL_ID = "deconstruct-document"
    SKILL_VERSION = "2.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: DocumentDeconstructorSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or DocumentDeconstructorSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        source_id = source["id"]
        segments = self.db.list_ndr_segments_for_source(source_id)

        if not segments:
            raise RuntimeError(f"No NDR segments found for source {source_id}.")

        skill_run = self.db.create_skill_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "skill_id": self.SKILL_ID,
                "skill_version": self.SKILL_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source_id,
                    "segment_count": len(segments),
                },
                "started_at": utc_now_iso(),
            },
        )
        skill_run_id = skill_run["id"]

        try:
            source_metadata = source.get("source_metadata") or {}
            if not isinstance(source_metadata, dict):
                source_metadata = {}

            output, execution = self.skill.run(
                source_metadata=source_metadata,
                segments=segments,
            )

            self.db.delete_document_chapters_for_source(source_id)
            chapter_rows = [
                {
                    "id": str(uuid.uuid4()),
                    "source_id": source_id,
                    "workspace_id": workspace_id,
                    "sequence_index": chapter.sequence_index,
                    "title": chapter.title,
                    "level": chapter.level,
                    "segment_ids": chapter.segment_ids,
                }
                for chapter in output.chapters
            ]
            created_chapters = self.db.insert_document_chapters(chapter_rows)

            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "completed",
                    "output": output.model_dump(),
                    "promoted": {
                        "source_ids": [source_id],
                        "chapter_ids": [str(row["id"]) for row in created_chapters],
                    },
                    **skill_run_completion_fields(execution),
                    "completed_at": utc_now_iso(),
                },
            )

            deconstructed_at = utc_now_iso()
            updated_metadata = {
                **source_metadata,
                "deconstruct": {
                    "deconstructed_at": deconstructed_at,
                    "chapter_count": len(output.chapters),
                    "segment_count": len(segments),
                },
            }
            self.db.update_source(
                source_id,
                {
                    "source_metadata": updated_metadata,
                },
            )
            source["source_metadata"] = updated_metadata

            return skill_run_id
        except Exception as exc:
            logger.exception("Skill run %s failed", skill_run_id)
            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


class ExtractChapterKnowledgeSkillExecutor:
    SKILL_ID = "extract-knowledge"
    SKILL_VERSION = "1.0.0"
    MODULE = "intellex"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: ExtractChapterKnowledgeSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or ExtractChapterKnowledgeSkill()

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

        skill_run = self.db.create_skill_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "skill_id": self.SKILL_ID,
                "skill_version": self.SKILL_VERSION,
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
        skill_run_id = skill_run["id"]

        try:
            source_metadata = source.get("source_metadata") or {}
            if not isinstance(source_metadata, dict):
                source_metadata = {}

            output, execution = self.skill.run(
                source_metadata=source_metadata,
                chapter_rows=chapter_rows,
                segments=segments,
                existing_labels=existing_labels,
            )

            inserts, updates, disputes = promote_concepts_to_wiki(
                workspace_id=workspace_id,
                source_id=source_id,
                skill_run_id=skill_run_id,
                skill_id=self.SKILL_ID,
                skill_version=self.SKILL_VERSION,
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

            self.db.update_skill_run(
                skill_run_id,
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
                    **skill_run_completion_fields(execution),
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

            return skill_run_id
        except Exception as exc:
            logger.exception("Skill run %s failed", skill_run_id)
            self.db.update_skill_run(
                skill_run_id,
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


def _run_mathesys_narration_skill(
    *,
    db: WorkerDatabase,
    storage: WorkerStorage,
    skill: Any,
    skill_id: str,
    skill_version: str,
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

    skill_inputs: dict[str, Any] = {
        "source_id": source_id,
        "segment_count": len(segments),
    }

    if include_wiki:
        skill_inputs["wiki_entry_count"] = len(wiki_entries)
    else:
        skill_inputs["chapter_count"] = len(chapter_rows)

    skill_run = db.create_skill_run(
        {
            "production_run_id": production_run_id,
            "workspace_id": workspace_id,
            "skill_id": skill_id,
            "skill_version": skill_version,
            "module": "mathesys",
            "status": "running",
            "inputs": skill_inputs,
            "started_at": utc_now_iso(),
        },
    )
    skill_run_id = skill_run["id"]

    try:
        source_metadata = source.get("source_metadata") or {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}

        volumes, execution = skill.run(
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
                        "skill_run_id": skill_run_id,
                        "skill_id": skill_id,
                        "skill_version": skill_version,
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

        db.update_skill_run(
            skill_run_id,
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
                **skill_run_completion_fields(execution, extra_calls=tts_calls or None),
                "completed_at": utc_now_iso(),
            },
        )
        return skill_run_id
    except Exception as exc:
        logger.exception("Skill run %s failed", skill_run_id)
        db.update_skill_run(
            skill_run_id,
            {
                "status": "failed",
                "error": str(exc),
                "completed_at": utc_now_iso(),
            },
        )
        raise


class ElevenReaderScriptSkillExecutor:
    SKILL_ID = "elevenreader-ebook"
    SKILL_VERSION = "2.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        skill: ElevenReaderScriptSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.skill = skill or ElevenReaderScriptSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_mathesys_narration_skill(
            db=self.db,
            storage=self.storage,
            skill=self.skill,
            skill_id=self.SKILL_ID,
            skill_version=self.SKILL_VERSION,
            artifact_type="eleven_reader_script",
            artifact_format="epub3",
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            include_wiki=False,
            extra_manifest=lambda volume: {
                "chapter_count": volume.get("chapter_count"),
                "chapter_titles": volume.get("chapter_titles"),
            },
        )


class SpeechifyApiSsmlSkillExecutor:
    SKILL_ID = "speechify-audio"
    SKILL_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        skill: SpeechifyApiSsmlSkill | None = None,
        client: SpeechifyClient | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.skill = skill or SpeechifyApiSsmlSkill()
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

        return _run_mathesys_narration_skill(
            db=self.db,
            storage=self.storage,
            skill=self.skill,
            skill_id=self.SKILL_ID,
            skill_version=self.SKILL_VERSION,
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


class ElevenLabsStructuredTextSkillExecutor:
    SKILL_ID = "elevenlabs-audio"
    SKILL_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        skill: ElevenLabsStructuredTextSkill | None = None,
        client: ElevenLabsClient | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.skill = skill or ElevenLabsStructuredTextSkill()
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
        return _run_mathesys_narration_skill(
            db=self.db,
            storage=self.storage,
            skill=self.skill,
            skill_id=self.SKILL_ID,
            skill_version=self.SKILL_VERSION,
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


class FlashcardGenSkillExecutor:
    SKILL_ID = "generate-flashcards"
    SKILL_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: FlashcardGenSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or FlashcardGenSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_qngen_skill(
            db=self.db,
            skill=self.skill,
            skill_id=self.SKILL_ID,
            skill_version=self.SKILL_VERSION,
            module=self.MODULE,
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            promote_items=lambda **kwargs: promote_flashcards(
                flashcards=kwargs["items"],
                workspace_id=kwargs["workspace_id"],
                source_id=kwargs["source_id"],
                production_run_id=kwargs["production_run_id"],
                skill_run_id=kwargs["skill_run_id"],
                skill_id=kwargs["skill_id"],
                skill_version=kwargs["skill_version"],
            ),
            insert_rows=self.db.insert_flashcards,
            output_key="flashcards",
            promoted_key="flashcard_ids",
        )


class QuizGenSkillExecutor:
    SKILL_ID = "generate-questions"
    SKILL_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: QuizGenSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or QuizGenSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_qngen_skill(
            db=self.db,
            skill=self.skill,
            skill_id=self.SKILL_ID,
            skill_version=self.SKILL_VERSION,
            module=self.MODULE,
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            promote_items=lambda **kwargs: promote_quizzes(
                questions=kwargs["items"],
                workspace_id=kwargs["workspace_id"],
                source_id=kwargs["source_id"],
                production_run_id=kwargs["production_run_id"],
                skill_run_id=kwargs["skill_run_id"],
                skill_id=kwargs["skill_id"],
                skill_version=kwargs["skill_version"],
            ),
            insert_rows=self.db.insert_quizzes,
            output_key="questions",
            promoted_key="quiz_ids",
        )


class ScenarioGenSkillExecutor:
    SKILL_ID = "generate-scenarios"
    SKILL_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: ScenarioGenSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or ScenarioGenSkill()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        return _run_qngen_skill(
            db=self.db,
            skill=self.skill,
            skill_id=self.SKILL_ID,
            skill_version=self.SKILL_VERSION,
            module=self.MODULE,
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            promote_items=lambda **kwargs: promote_scenarios(
                scenarios=kwargs["items"],
                workspace_id=kwargs["workspace_id"],
                source_id=kwargs["source_id"],
                production_run_id=kwargs["production_run_id"],
                skill_run_id=kwargs["skill_run_id"],
                skill_id=kwargs["skill_id"],
                skill_version=kwargs["skill_version"],
            ),
            insert_rows=self.db.insert_scenarios,
            output_key="scenarios",
            promoted_key="scenario_ids",
        )


class AssessmentSetGenSkillExecutor:
    SKILL_ID = "assessment-set-gen"
    SKILL_VERSION = "1.0.0"
    MODULE = "qngen"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        skill: AssessmentSetGenSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.skill = skill or AssessmentSetGenSkill()

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

        has_deconstruct_skill_run = self.db.has_completed_skill_run_for_source(
            source_id,
            DocumentDeconstructorSkillExecutor.SKILL_ID,
        )
        has_extract_skill_run = self.db.has_completed_skill_run_for_source(
            source_id,
            ExtractChapterKnowledgeSkillExecutor.SKILL_ID,
        )
        has_document_chapters = self.db.has_document_chapters_for_source(source_id)
        if not source_intellex_complete(
            source,
            has_segments=True,
            has_document_chapters=has_document_chapters,
            has_deconstruct_skill_run=has_deconstruct_skill_run,
            has_extract_skill_run=has_extract_skill_run,
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

        skill_run = self.db.create_skill_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "skill_id": self.SKILL_ID,
                "skill_version": self.SKILL_VERSION,
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
        skill_run_id = skill_run["id"]

        try:
            source_metadata = source.get("source_metadata") or {}
            if not isinstance(source_metadata, dict):
                source_metadata = {}

            output, execution = self.skill.run(
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
                skill_run_id=skill_run_id,
                skill_id=self.SKILL_ID,
                skill_version=self.SKILL_VERSION,
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
                **skill_run_completion_fields(execution),
                "completed_at": utc_now_iso(),
            }
            self.db.update_skill_run(skill_run_id, db_update)
            return skill_run_id
        except Exception as exc:
            logger.exception("Skill run %s failed", skill_run_id)
            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "failed",
                    "error": str(exc),
                    "completed_at": utc_now_iso(),
                },
            )
            raise


def _run_qngen_skill(
    *,
    db: WorkerDatabase,
    skill: Any,
    skill_id: str,
    skill_version: str,
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

    skill_run = db.create_skill_run(
        {
            "production_run_id": production_run_id,
            "workspace_id": workspace_id,
            "skill_id": skill_id,
            "skill_version": skill_version,
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
    skill_run_id = skill_run["id"]

    try:
        source_metadata = source.get("source_metadata") or {}
        if not isinstance(source_metadata, dict):
            source_metadata = {}

        output, execution = skill.run(
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
            skill_run_id=skill_run_id,
            skill_id=skill_id,
            skill_version=skill_version,
        )
        created_rows = insert_rows(rows)
        promoted_ids = [str(row["id"]) for row in created_rows]

        db.update_skill_run(
            skill_run_id,
            {
                "status": "completed",
                "output": output_data,
                "promoted": {promoted_key: promoted_ids},
                **skill_run_completion_fields(execution),
                "completed_at": utc_now_iso(),
            },
        )
        return skill_run_id
    except Exception as exc:
        logger.exception("Skill run %s failed", skill_run_id)
        db.update_skill_run(
            skill_run_id,
            {
                "status": "failed",
                "error": str(exc),
                "completed_at": utc_now_iso(),
            },
        )
        raise
