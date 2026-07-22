from __future__ import annotations

from typing import Any

from app.worker.pipeline_runner import PipelineRunner
from app.worker.wiki_ingest_transcription import run_wiki_ingest_transcription


def orchestrate_production_run(production_run_id: str) -> dict[str, Any]:
    """Run deterministic ingest steps for a production run."""
    runner = PipelineRunner()
    return runner.execute(production_run_id)


def transcribe_wiki_ingest_batch(batch_id: str) -> dict[str, Any]:
    """Transcribe wiki note attachments into raw_notes for author review."""
    return run_wiki_ingest_transcription(batch_id)
