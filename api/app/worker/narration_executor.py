"""Generate Narration stage: per-paragraph ElevenLabs TTS with word timings.

Walks each source's document_chapters in reading order and synthesizes every
paragraph ndr_segment that does not yet have narration for the configured
voice (idempotent re-runs). Audio is stored per segment in the sources bucket
(`<source dir>/narration/<voice_id>/<segment_id>.mp3`) and the word-level
timings land on the narration_segments row, so the Reader can highlight the
spoken word from the row alone — no alignment files to fetch.

Per-segment requests keep every alignment scoped to exactly one segment's
plain text (the same tokenization the Reader uses), which is what makes the
word indexes trustworthy. Prosody continuity across paragraph boundaries comes
from ElevenLabs request stitching (previous_request_ids + next_text).

The downloadable artifact is a small JSON manifest (chapter grouping, timings,
and sources-bucket audio paths) — not a zip of MP3s — so stage completion stays
under Storage size limits while the Reader uses the per-segment files.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.intellex.wiki_slug import normalize_slug
from app.services.api_pricing import cost_elevenlabs_usage
from app.services.elevenlabs_client import ElevenLabsClient, ElevenLabsError
from app.services.stage_run_billing import stage_run_completion_fields
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _narration_path(storage_path: str, voice_id: str, segment_id: str) -> str:
    parent = storage_path.rsplit("/", 1)[0]
    return f"{parent}/narration/{voice_id}/{segment_id}.mp3"


def _progress_output(
    *,
    done: int,
    total: int,
    narrated: int,
    reused: int,
    skipped: int,
    character_count: int,
    voice_id: str,
    model_id: str,
) -> dict[str, Any]:
    """Stage-run output shape used both mid-run (live UI) and at completion."""
    return {
        "summary": f"{done}/{total} segments",
        "segments_done": done,
        "segments_total": total,
        "segments_narrated": narrated,
        "segments_reused": reused,
        "segments_skipped": skipped,
        "character_count": character_count,
        "voice_id": voice_id,
        "model_id": model_id,
    }


def _paragraph_rows_for_chapter(
    chapter: dict[str, Any],
    segments: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        segments[segment_id]
        for segment_id in chapter.get("segment_ids") or []
        if segment_id in segments and segments[segment_id].get("kind") == "paragraph"
    ]


class NarrationStageExecutor:
    """Stage: GENERATE-NARRATION -- synthesize read-while-listen audio."""

    STAGE_ID = "generate-narration"
    STAGE_VERSION = "1.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
        client: ElevenLabsClient | None = None,
        max_segment_chars: int | None = None,
    ) -> None:
        from app.config import get_settings

        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self.client = client or ElevenLabsClient()
        self.max_segment_chars = (
            max_segment_chars or get_settings().narration.max_segment_chars
        )

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        stage_run = self.db.create_stage_run(
            {
                "production_run_id": production_run_id,
                "workspace_id": workspace_id,
                "stage_id": self.STAGE_ID,
                "stage_version": self.STAGE_VERSION,
                "module": self.MODULE,
                "status": "running",
                "inputs": {
                    "source_id": source["id"],
                    "voice_id": self.client.voice_id,
                    "model_id": self.client.model_id,
                },
                "started_at": utc_now_iso(),
            }
        )
        stage_run_id = stage_run["id"]

        try:
            output, character_count, publish_context = self._narrate_source(
                workspace_id=workspace_id,
                source=source,
                stage_run_id=stage_run_id,
            )
            artifact_file = self._publish_artifact(
                workspace_id=workspace_id,
                production_run_id=production_run_id,
                stage_run_id=stage_run_id,
                source=source,
                **publish_context,
            )
            promoted: dict[str, Any] = {"source_ids": [source["id"]]}
            if artifact_file:
                output["files"] = [artifact_file]
                promoted["artifact_ids"] = [artifact_file["artifact_id"]]
            extra_calls = (
                [
                    cost_elevenlabs_usage(
                        model=self.client.model_id,
                        character_count=character_count,
                    )
                ]
                if character_count
                else []
            )
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "completed",
                    "output": output,
                    "promoted": promoted,
                    **stage_run_completion_fields(
                        {"model": self.client.model_id, "token_usage": {}},
                        extra_calls=extra_calls,
                    ),
                    "completed_at": utc_now_iso(),
                },
            )
            return stage_run_id
        except Exception as exc:
            logger.exception("Narration stage run %s failed", stage_run_id)
            self.db.update_stage_run(
                stage_run_id,
                {"status": "failed", "error": str(exc), "completed_at": utc_now_iso()},
            )
            raise

    def _publish_progress(
        self,
        stage_run_id: str,
        *,
        done: int,
        total: int,
        narrated: int,
        reused: int,
        skipped: int,
        character_count: int,
    ) -> dict[str, Any]:
        output = _progress_output(
            done=done,
            total=total,
            narrated=narrated,
            reused=reused,
            skipped=skipped,
            character_count=character_count,
            voice_id=self.client.voice_id,
            model_id=self.client.model_id,
        )
        self.db.update_stage_run(stage_run_id, {"output": output})
        return output

    def _narrate_source(
        self,
        *,
        workspace_id: str,
        source: dict[str, Any],
        stage_run_id: str,
    ) -> tuple[dict[str, Any], int, dict[str, Any]]:
        if not self.client.enabled:
            raise ElevenLabsError(
                "ELEVENLABS_API_KEY is not configured; cannot generate narration."
            )

        source_id = source["id"]
        storage_path = source.get("storage_path")
        if not storage_path:
            raise RuntimeError(f"Source {source_id} has no storage path.")

        segments = {
            row["id"]: row for row in self.db.list_ndr_segments_for_source(source_id)
        }
        chapters = self.db.list_document_chapters_for_source(source_id)
        if not chapters:
            raise RuntimeError(
                f"Source {source_id} has no document chapters; run the base pipeline first."
            )

        already = self.db.list_narrated_segment_ids_for_source(
            source_id, self.client.voice_id
        )

        chapter_paragraphs = [
            _paragraph_rows_for_chapter(chapter, segments) for chapter in chapters
        ]
        segments_total = sum(len(rows) for rows in chapter_paragraphs)

        narrated = 0
        reused = 0
        skipped = 0
        done = 0
        character_count = 0
        previous_request_ids: list[str] = []

        def publish() -> dict[str, Any]:
            return self._publish_progress(
                stage_run_id,
                done=done,
                total=segments_total,
                narrated=narrated,
                reused=reused,
                skipped=skipped,
                character_count=character_count,
            )

        # Seed progress so the console shows 0/N before the first TTS round-trip.
        output = publish()

        for chapter, paragraph_rows in zip(chapters, chapter_paragraphs, strict=True):
            for index, row in enumerate(paragraph_rows):
                if row["id"] in already:
                    reused += 1
                    # A gap in request stitching; the next request starts fresh.
                    previous_request_ids = []
                    done += 1
                    output = publish()
                    continue

                text = (row.get("text") or "").strip()
                if not text:
                    skipped += 1
                    done += 1
                    output = publish()
                    continue
                if len(text) > self.max_segment_chars:
                    logger.warning(
                        "Segment %s is %d chars (> %d); skipping narration for it.",
                        row["id"],
                        len(text),
                        self.max_segment_chars,
                    )
                    skipped += 1
                    previous_request_ids = []
                    done += 1
                    output = publish()
                    continue

                next_text = (
                    paragraph_rows[index + 1].get("text")
                    if index + 1 < len(paragraph_rows)
                    else None
                )
                result = self.client.synthesize_with_timestamps(
                    text,
                    previous_request_ids=previous_request_ids,
                    next_text=next_text,
                )

                audio_path = _narration_path(
                    storage_path, self.client.voice_id, row["id"]
                )
                self.storage.upload(
                    audio_path,
                    result.audio,
                    bucket=self.storage.sources_bucket,
                    content_type="audio/mpeg",
                )
                self.db.insert_narration_segment(
                    {
                        "workspace_id": workspace_id,
                        "source_id": source_id,
                        "chapter_id": chapter.get("id"),
                        "segment_id": row["id"],
                        "voice_id": self.client.voice_id,
                        "model_id": self.client.model_id,
                        "audio_path": audio_path,
                        "duration_seconds": result.duration_seconds,
                        "words": [word.to_dict() for word in result.words],
                        "request_id": result.request_id,
                        "character_count": result.character_cost,
                    }
                )

                narrated += 1
                character_count += result.character_cost
                if result.request_id:
                    previous_request_ids = (previous_request_ids + [result.request_id])[-3:]

                done += 1
                output = publish()

            # Chapters are natural narration breaks; do not stitch across them.
            previous_request_ids = []

        publish_context = {
            "chapters": chapters,
            "segments": segments,
        }
        return output, character_count, publish_context

    def _artifact_title(self, source: dict[str, Any]) -> str:
        research = (source.get("source_metadata") or {}).get("research") or {}
        if not isinstance(research, dict):
            research = {}
        return str(research.get("title") or source.get("filename") or "Untitled")

    def _publish_artifact(
        self,
        *,
        workspace_id: str,
        production_run_id: str,
        stage_run_id: str,
        source: dict[str, Any],
        chapters: list[dict[str, Any]],
        segments: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Publish a JSON manifest of narrated segments as the downloadable artifact.

        Per-segment MP3s stay in the sources bucket (Reader source of truth). The
        artifact is a small export: chapter grouping, word timings, and each
        segment's audio_path — usable without embedding audio bytes.
        """
        rows = self.db.list_narration_segments_for_source(
            source["id"], self.client.voice_id
        )
        by_segment = {row["segment_id"]: row for row in rows}
        if not by_segment:
            return None

        title = self._artifact_title(source)
        filename = f"{normalize_slug(title)}-narration.json"

        manifest_chapters: list[dict[str, Any]] = []
        total_duration = 0.0
        segment_total = 0

        for chapter in chapters:
            entries: list[dict[str, Any]] = []
            for segment_id in chapter.get("segment_ids") or []:
                row = by_segment.get(segment_id)
                if row is None:
                    continue
                segment = segments.get(segment_id) or {}
                sequence_index = int(segment.get("sequence_index") or 0)
                duration = float(row.get("duration_seconds") or 0)
                total_duration += duration
                segment_total += 1
                entries.append(
                    {
                        "segment_id": segment_id,
                        "sequence_index": sequence_index,
                        "audio_path": row.get("audio_path"),
                        "duration_seconds": duration,
                        "character_count": row.get("character_count"),
                        "words": row.get("words") or [],
                    }
                )
            if entries:
                manifest_chapters.append(
                    {
                        "title": chapter.get("title"),
                        "sequence_index": chapter.get("sequence_index"),
                        "segments": entries,
                    }
                )

        manifest = {
            "source_id": source["id"],
            "title": title,
            "voice_id": self.client.voice_id,
            "model_id": self.client.model_id,
            "generated_at": utc_now_iso(),
            "segment_count": segment_total,
            "total_duration_seconds": round(total_duration, 3),
            "chapters": manifest_chapters,
        }
        manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode(
            "utf-8"
        )

        artifact = self.db.create_artifact(
            {
                "workspace_id": workspace_id,
                "source_id": source["id"],
                "production_run_id": production_run_id,
                "artifact_type": "narration_audio",
                "format": "json",
                "filename": filename,
                "storage_path": "pending",
                "file_size_bytes": 0,
                "manifest": {
                    "voice_id": self.client.voice_id,
                    "model_id": self.client.model_id,
                    "segment_count": segment_total,
                    "chapter_count": len(manifest_chapters),
                    "chapter_titles": [c["title"] for c in manifest_chapters],
                    "total_duration_seconds": round(total_duration, 3),
                },
                "origin": {
                    "stage_run_id": stage_run_id,
                    "stage_id": self.STAGE_ID,
                    "stage_version": self.STAGE_VERSION,
                },
            }
        )
        artifact_id = artifact["id"]
        storage_path = f"workspaces/{workspace_id}/artifacts/{artifact_id}/{filename}"
        self.storage.upload(
            storage_path, manifest_bytes, content_type="application/json"
        )
        self.db.update_artifact(
            artifact_id,
            {"storage_path": storage_path, "file_size_bytes": len(manifest_bytes)},
        )

        return {
            "artifact_id": artifact_id,
            "filename": filename,
            "storage_path": storage_path,
            "file_size_bytes": len(manifest_bytes),
        }
