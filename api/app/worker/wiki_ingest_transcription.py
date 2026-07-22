"""RQ job: download wiki-ingest attachments and fill raw_notes."""

from __future__ import annotations

import logging
from typing import Any

from app.services.llamaparse_client import LlamaParseClient
from app.services.wiki_transcription import (
    WikiTranscriptionError,
    transcribe_attachments_in_order,
)
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def run_wiki_ingest_transcription(batch_id: str) -> dict[str, Any]:
    db = WorkerDatabase()
    storage = WorkerStorage()
    batch = db.get_wiki_ingest_batch(batch_id)

    if not batch:
        raise RuntimeError(f"Wiki ingest batch {batch_id} not found.")

    if batch.get("status") != "transcribing":
        return {
            "batch_id": batch_id,
            "status": batch.get("status"),
            "skipped": True,
        }

    attachments = batch.get("attachments") or []
    if not isinstance(attachments, list) or not attachments:
        db.update_wiki_ingest_batch(
            batch_id,
            {
                "status": "failed",
                "transcription_error": "No attachments to transcribe.",
            },
        )
        return {"batch_id": batch_id, "status": "failed"}

    try:
        items: list[tuple[dict[str, Any], bytes]] = []
        for attachment in attachments:
            if not isinstance(attachment, dict):
                raise WikiTranscriptionError("Attachment metadata is invalid.")
            path = str(attachment.get("storage_path") or "")
            if not path:
                raise WikiTranscriptionError("Attachment is missing storage_path.")
            content = storage.download(path, bucket=storage.sources_bucket)
            items.append((attachment, content))

        raw_notes = transcribe_attachments_in_order(
            items,
            llamaparse=LlamaParseClient(),
        )
        updated = db.update_wiki_ingest_batch(
            batch_id,
            {
                "status": "transcribed",
                "raw_notes": raw_notes,
                "transcription_error": None,
            },
        )
        return {
            "batch_id": batch_id,
            "status": "transcribed",
            "raw_notes_chars": len(raw_notes),
            "attachment_count": len(items),
            "updated_at": updated.get("updated_at"),
        }
    except Exception as exc:  # noqa: BLE001 - persist failure onto the batch
        message = str(exc) or exc.__class__.__name__
        logger.exception("Wiki ingest transcription failed for batch %s", batch_id)
        db.update_wiki_ingest_batch(
            batch_id,
            {
                "status": "failed",
                "transcription_error": message[:2000],
            },
        )
        return {"batch_id": batch_id, "status": "failed", "error": message}
