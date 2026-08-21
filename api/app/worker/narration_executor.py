"""Generate Narration stage: per-chapter TTS with word timings.

Walks each source's document_chapters in reading order and synthesizes one
MP3 per chapter for the configured voice (idempotent re-runs). If a chapter's
joined paragraph text exceeds the provider character cap, it is packed into
the fewest clips that fit, always splitting on paragraph boundaries. A single
paragraph over the cap is skipped.

Audio is stored at `<source dir>/narration/<voice_id>/<chapter_id>-<clip>.mp3`.
Each paragraph keeps a `narration_segments` row pointing at that shared file,
with word timings on the clip timeline so the Reader can highlight and seek.

The downloadable artifact is a small JSON manifest (chapter grouping, timings,
and sources-bucket audio paths) — not a zip of MP3s.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.artifact_paths import downloadable_artifact_path
from app.intellex.wiki_slug import normalize_slug
from app.services.api_pricing import cost_tts_usage
from app.services.elevenlabs_client import ElevenLabsError, WordTiming
from app.services.speechify_client import SpeechifyError
from app.services.tts.factory import TtsClient, get_tts_client
from app.services.stage_run_billing import stage_run_completion_fields
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _narration_path(
    storage_path: str, voice_id: str, chapter_id: str, clip_index: int
) -> str:
    parent = storage_path.rsplit("/", 1)[0]
    return f"{parent}/narration/{voice_id}/{chapter_id}-{clip_index:02d}.mp3"


_CLIP_JOIN = "\n\n"


def _paragraph_text(row: dict[str, Any]) -> str:
    return str(row.get("text") or "").strip()


def _joined_clip_text(paragraphs: list[dict[str, Any]]) -> str:
    return _CLIP_JOIN.join(
        text for text in (_paragraph_text(row) for row in paragraphs) if text
    )


def pack_chapter_clips(
    paragraphs: list[dict[str, Any]],
    max_chars: int,
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]], int]:
    """Pack chapter paragraphs into TTS clips that fit under `max_chars`.

    Returns (clips, oversize_paragraphs, empty_count). Clips never split a
    paragraph. A paragraph longer than the cap is omitted rather than truncated.
    """
    clips: list[list[dict[str, Any]]] = []
    oversize: list[dict[str, Any]] = []
    empty_count = 0
    current: list[dict[str, Any]] = []
    current_len = 0

    for row in paragraphs:
        text = _paragraph_text(row)
        if not text:
            empty_count += 1
            continue
        if len(text) > max_chars:
            if current:
                clips.append(current)
                current = []
                current_len = 0
            oversize.append(row)
            continue
        extra = len(text) if not current else len(_CLIP_JOIN) + len(text)
        if current and current_len + extra > max_chars:
            clips.append(current)
            current = [row]
            current_len = len(text)
        else:
            current.append(row)
            current_len += extra

    if current:
        clips.append(current)
    return clips, oversize, empty_count


def assign_words_to_paragraphs(
    paragraphs: list[dict[str, Any]],
    words: list[WordTiming],
) -> list[list[WordTiming]]:
    """Slice clip-level word timings onto each paragraph's token stream."""
    assigned: list[list[WordTiming]] = []
    cursor = 0
    for row in paragraphs:
        n = len(_paragraph_text(row).split())
        chunk = words[cursor : cursor + n]
        assigned.append(
            [
                WordTiming(index=i, word=word.word, start=word.start, end=word.end)
                for i, word in enumerate(chunk)
            ]
        )
        cursor += n
    if cursor != len(words):
        logger.warning(
            "Clip alignment produced %d words for %d expected tokens; "
            "highlighting may drift in this chapter clip.",
            len(words),
            cursor,
        )
    return assigned


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
        "summary": f"{done}/{total} clips",
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
        client: TtsClient | None = None,
        max_segment_chars: int | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()
        self._client = client
        self._max_segment_chars = max_segment_chars

    @property
    def client(self) -> TtsClient:
        if self._client is None:
            self._client = get_tts_client()
        return self._client

    @property
    def max_segment_chars(self) -> int:
        if self._max_segment_chars is not None:
            return self._max_segment_chars
        return self.client.max_segment_chars

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
                    cost_tts_usage(
                        provider=getattr(self.client, "provider", "elevenlabs"),
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
            fail_payload: dict[str, Any] = {
                "status": "failed",
                "error": str(exc),
                "completed_at": utc_now_iso(),
            }
            try:
                artifact_file = self._publish_artifact(
                    workspace_id=workspace_id,
                    production_run_id=production_run_id,
                    stage_run_id=stage_run_id,
                    source=source,
                )
            except Exception:
                logger.exception(
                    "Failed to publish partial narration artifact for stage run %s",
                    stage_run_id,
                )
                artifact_file = None
            if artifact_file:
                fail_payload["promoted"] = {
                    "source_ids": [source["id"]],
                    "artifact_ids": [artifact_file["artifact_id"]],
                }
            self.db.update_stage_run(stage_run_id, fail_payload)
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
            provider = getattr(self.client, "provider", "tts")
            key_name = (
                "SPEECHIFY_API_KEY" if provider == "speechify" else "ELEVENLABS_API_KEY"
            )
            error_cls = SpeechifyError if provider == "speechify" else ElevenLabsError
            raise error_cls(
                f"{key_name} is not configured; cannot generate narration."
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

        existing_rows = {
            row["segment_id"]: row
            for row in self.db.list_narration_segments_for_source(
                source_id, self.client.voice_id
            )
        }

        packed: list[tuple[dict[str, Any], int, list[dict[str, Any]]]] = []
        skipped = 0
        for chapter in chapters:
            paragraph_rows = _paragraph_rows_for_chapter(chapter, segments)
            clips, oversize, empty_count = pack_chapter_clips(
                paragraph_rows, self.max_segment_chars
            )
            skipped += empty_count
            for row in oversize:
                logger.warning(
                    "Paragraph %s is %d chars (> %d); skipping narration for it.",
                    row["id"],
                    len(_paragraph_text(row)),
                    self.max_segment_chars,
                )
                skipped += 1
            for clip_index, clip_rows in enumerate(clips):
                packed.append((chapter, clip_index, clip_rows))

        clips_total = len(packed)
        narrated = 0
        reused = 0
        done = 0
        character_count = 0
        previous_request_ids: list[str] = []

        def publish() -> dict[str, Any]:
            return self._publish_progress(
                stage_run_id,
                done=done,
                total=clips_total,
                narrated=narrated,
                reused=reused,
                skipped=skipped,
                character_count=character_count,
            )

        # Seed progress so the console shows 0/N before the first TTS round-trip.
        output = publish()

        last_chapter_id: str | None = None
        for chapter, clip_index, clip_rows in packed:
            chapter_id = str(chapter.get("id") or "")
            if last_chapter_id is not None and chapter_id != last_chapter_id:
                previous_request_ids = []
            last_chapter_id = chapter_id

            audio_path = _narration_path(
                storage_path, self.client.voice_id, chapter_id, clip_index
            )
            clip_ids = [str(row["id"]) for row in clip_rows]
            if clip_ids and all(
                existing_rows.get(segment_id, {}).get("audio_path") == audio_path
                for segment_id in clip_ids
            ):
                reused += 1
                previous_request_ids = []
                done += 1
                output = publish()
                continue

            text = _joined_clip_text(clip_rows)
            result = self.client.synthesize_with_timestamps(
                text,
                previous_request_ids=previous_request_ids,
            )
            per_paragraph_words = assign_words_to_paragraphs(clip_rows, result.words)

            self.storage.upload(
                audio_path,
                result.audio,
                bucket=self.storage.sources_bucket,
                content_type="audio/mpeg",
            )
            for row, words in zip(clip_rows, per_paragraph_words, strict=True):
                self.db.upsert_narration_segment(
                    {
                        "workspace_id": workspace_id,
                        "source_id": source_id,
                        "chapter_id": chapter.get("id"),
                        "segment_id": row["id"],
                        "voice_id": self.client.voice_id,
                        "model_id": self.client.model_id,
                        "audio_path": audio_path,
                        "duration_seconds": result.duration_seconds,
                        "words": [word.to_dict() for word in words],
                        "request_id": result.request_id,
                        "character_count": result.character_cost,
                    }
                )
                existing_rows[str(row["id"])] = {"audio_path": audio_path}

            narrated += 1
            character_count += result.character_cost
            if result.request_id:
                previous_request_ids = (previous_request_ids + [result.request_id])[-3:]

            done += 1
            output = publish()

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
        chapters: list[dict[str, Any]] | None = None,
        segments: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Publish a JSON manifest of narrated chapter clips as the downloadable artifact.

        Per-chapter MP3s stay in the sources bucket (Reader source of truth). The
        artifact is a small export: chapter grouping, word timings, and each
        paragraph's shared audio_path — usable without embedding audio bytes.

        Called on success and after a partial failure so clips already written
        still get an `artifacts` row.
        """
        source_id = source["id"]
        if chapters is None:
            chapters = self.db.list_document_chapters_for_source(source_id)
        if segments is None:
            segments = {
                row["id"]: row
                for row in self.db.list_ndr_segments_for_source(source_id)
            }
        rows = self.db.list_narration_segments_for_source(
            source_id, self.client.voice_id
        )
        by_segment = {row["segment_id"]: row for row in rows}
        if not by_segment:
            return None

        title = self._artifact_title(source)
        filename = f"{normalize_slug(title)}-narration.json"

        manifest_chapters: list[dict[str, Any]] = []
        total_duration = 0.0
        segment_total = 0
        billed_paths: set[str] = set()

        for chapter in chapters:
            entries: list[dict[str, Any]] = []
            for segment_id in chapter.get("segment_ids") or []:
                row = by_segment.get(segment_id)
                if row is None:
                    continue
                segment = segments.get(segment_id) or {}
                sequence_index = int(segment.get("sequence_index") or 0)
                duration = float(row.get("duration_seconds") or 0)
                path = str(row.get("audio_path") or "")
                if path and path not in billed_paths:
                    billed_paths.add(path)
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
            "clip_count": len(billed_paths),
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
                    "clip_count": len(billed_paths),
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
        storage_path = downloadable_artifact_path(
            source["storage_path"], "narration_audio", artifact_id, filename
        )
        self.storage.upload(
            storage_path,
            manifest_bytes,
            bucket=self.storage.sources_bucket,
            content_type="application/json",
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
