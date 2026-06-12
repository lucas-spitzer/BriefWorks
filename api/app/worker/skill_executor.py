from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.intellex.models import ParsedDocument
from app.intellex.skills.document_deconstructor import DocumentDeconstructorSkill
from app.intellex.skills.promotion import merge_research_into_source_metadata
from app.intellex.skills.source_research import SourceResearchSkill
from app.intellex.skills.wiki_promotion import promote_concepts_to_wiki, resolve_prerequisites
from app.intellex.wiki_slug import normalize_slug
from app.mathesys.skills.eleven_reader_script import ElevenReaderScriptSkill
from app.mathesys.skills.elevenlabs_structured_text import ElevenLabsStructuredTextSkill
from app.mathesys.skills.speechify_api_ssml import SpeechifyApiSsmlSkill
from app.mathesys.skills.speechify_app_epub import SpeechifyAppEpubSkill
from app.qngen.assessment_promotion import (
    promote_flashcards,
    promote_quizzes,
    promote_scenarios,
)
from app.qngen.skills.flashcard_gen import FlashcardGenSkill
from app.qngen.skills.quiz_gen import QuizGenSkill
from app.qngen.skills.scenario_gen import ScenarioGenSkill
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
                    "model": execution["model"],
                    "token_usage": execution["token_usage"],
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


class DocumentDeconstructorSkillExecutor:
    SKILL_ID = "document-deconstructor"
    SKILL_VERSION = "1.0.0"
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
                existing_labels=existing_labels,
            )

            inserts, updates, disputes = promote_concepts_to_wiki(
                workspace_id=workspace_id,
                source_id=source_id,
                skill_run_id=skill_run_id,
                skill_id=self.SKILL_ID,
                skill_version=self.SKILL_VERSION,
                concepts=output.concepts,
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
                concepts=output.concepts,
                wiki_rows=list(slug_to_row.values()),
            )

            for update in prerequisite_updates:
                wiki_id = update.pop("id")
                self.db.update_wiki_entry(wiki_id, update)

            wiki_entry_ids = [
                str(slug_to_row[normalize_slug(concept.term_label)]["id"])
                for concept in output.concepts
                if normalize_slug(concept.term_label) in slug_to_row
            ]

            self.db.update_skill_run(
                skill_run_id,
                {
                    "status": "completed",
                    "output": output.model_dump(),
                    "promoted": {
                        "wiki_entry_ids": wiki_entry_ids,
                        "dispute_ids": [],
                        "disputes_logged": len(disputes),
                    },
                    "model": execution["model"],
                    "token_usage": execution["token_usage"],
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
) -> str:
    source_id = source["id"]
    segments = db.list_ndr_segments_for_source(source_id)

    if not segments:
        raise RuntimeError(f"No NDR segments found for source {source_id}.")

    wiki_entries = [
        entry
        for entry in db.list_wiki_entries_for_workspace(workspace_id)
        if entry.get("status") == "canonical"
    ]

    skill_run = db.create_skill_run(
        {
            "production_run_id": production_run_id,
            "workspace_id": workspace_id,
            "skill_id": skill_id,
            "skill_version": skill_version,
            "module": "mathesys",
            "status": "running",
            "inputs": {
                "source_id": source_id,
                "segment_count": len(segments),
                "wiki_entry_count": len(wiki_entries),
            },
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
        )

        artifact_ids: list[str] = []
        artifact_files: list[dict[str, Any]] = []

        for volume in volumes:
            file_bytes, content_type, extension = _serialize_narration_volume(volume)
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
            }

            if extra_manifest:
                manifest.update(extra_manifest(volume))

            artifact_row = db.create_artifact(
                {
                    "workspace_id": workspace_id,
                    "source_id": source_id,
                    "production_run_id": production_run_id,
                    "artifact_type": artifact_type,
                    "format": artifact_format,
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
                "model": execution["model"],
                "token_usage": execution["token_usage"],
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
    SKILL_ID = "eleven-reader-script"
    SKILL_VERSION = "1.0.0"
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
        )


class SpeechifyAppEpubSkillExecutor:
    SKILL_ID = "speechify-app-epub"
    SKILL_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        skill: SpeechifyAppEpubSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.skill = skill or SpeechifyAppEpubSkill()

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
            artifact_type="speechify_script",
            artifact_format="epub3",
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
        )


class SpeechifyApiSsmlSkillExecutor:
    SKILL_ID = "speechify-api-ssml"
    SKILL_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        skill: SpeechifyApiSsmlSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.skill = skill or SpeechifyApiSsmlSkill()

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
            artifact_type="speechify_audio",
            artifact_format="ssml",
            production_run_id=production_run_id,
            workspace_id=workspace_id,
            source=source,
            extra_manifest=lambda volume: {
                "section_count": volume.get("section_count"),
                "estimated_character_count": volume.get("estimated_character_count"),
            },
        )


class ElevenLabsStructuredTextSkillExecutor:
    SKILL_ID = "elevenlabs-structured-text"
    SKILL_VERSION = "1.0.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        skill: ElevenLabsStructuredTextSkill | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.skill = skill or ElevenLabsStructuredTextSkill()

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
        )


class FlashcardGenSkillExecutor:
    SKILL_ID = "flashcard-gen"
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
    SKILL_ID = "quiz-gen"
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
    SKILL_ID = "scenario-gen"
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
                "model": execution["model"],
                "token_usage": execution["token_usage"],
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
