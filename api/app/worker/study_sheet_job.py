"""RQ job: generate a study_sheet PDF artifact from an uploaded file."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.artifact_paths import OUTPUT_FILENAMES, downloadable_artifact_path
from app.config import get_settings
from app.mathesys.study_sheet.generate import (
    StudySheetError,
    StudySheetSource,
    generate_study_sheet,
)
from app.mathesys.study_sheet.printer import WeasyPrintPdfPrinter
from app.services.api_pricing import cost_llm_usage
from app.services.llm import get_llm_client
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def run_study_sheet_job(job_id: str) -> dict[str, Any]:
    settings = get_settings()
    db = WorkerDatabase()
    storage = WorkerStorage()
    job = db.get_study_sheet_job(job_id)

    if not job:
        raise RuntimeError(f"Study sheet job {job_id} not found.")

    if job.get("status") != "queued":
        return {
            "job_id": job_id,
            "status": job.get("status"),
            "skipped": True,
        }

    db.update_study_sheet_job(job_id, {"status": "running"})

    try:
        source_id = str(job.get("source_id") or "")
        sources = db.get_sources([source_id]) if source_id else []
        source = sources[0] if sources else None
        if source is None:
            raise RuntimeError(f"Study sheet job {job_id} has no source.")

        content = storage.download(str(job["input_storage_path"]))
        sheet_source = StudySheetSource(
            filename=str(job["input_filename"]),
            mime_type=str(job["input_mime_type"]),
            content=content,
        )
        result = generate_study_sheet(
            source=sheet_source,
            completer=get_llm_client("study_sheet"),
            printer=WeasyPrintPdfPrinter(),
            max_attempts=settings.study_sheet.max_attempts,
        )
        cost = _total_cost(result.provider, result.model, result.token_usages)
        pdf_name = OUTPUT_FILENAMES["study_sheet"]
        pdf_path = downloadable_artifact_path(source, "study_sheet")
        storage.upload(pdf_path, result.pdf, content_type="application/pdf")
        artifact_payload = {
            "workspace_id": job["workspace_id"],
            "source_id": source["id"],
            "production_run_id": None,
            "artifact_type": "study_sheet",
            "format": "pdf",
            "filename": pdf_name,
            "storage_path": pdf_path,
            "file_size_bytes": len(result.pdf),
            "manifest": {
                "module": "mathesys",
                "title": result.title,
                "page_count": result.page_count,
                "attempts": result.attempt_count,
            },
            "origin": {
                "job_id": job_id,
                "input_filename": job["input_filename"],
                "model": result.model,
                "provider": result.provider,
            },
        }
        existing = db.list_artifacts_for_source(source["id"], artifact_type="study_sheet")
        if existing:
            artifact = db.update_artifact(existing[0]["id"], artifact_payload)
        else:
            artifact = db.create_artifact(artifact_payload)
        updated = db.update_study_sheet_job(
            job_id,
            {
                "status": "completed",
                "artifact_id": artifact["id"],
                "attempt_count": result.attempt_count,
                "page_count": result.page_count,
                "error": None,
                "model": result.model,
                "cost_usd": cost,
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
        return {
            "job_id": job_id,
            "status": "completed",
            "artifact_id": artifact["id"],
            "page_count": result.page_count,
            "updated_at": updated.get("updated_at"),
        }
    except Exception as exc:  # noqa: BLE001 - persist failure onto the job
        message = str(exc) or exc.__class__.__name__
        logger.exception("Study sheet generation failed for job %s", job_id)
        db.update_study_sheet_job(
            job_id,
            {
                "status": "failed",
                "error": message[:2000],
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
        if isinstance(exc, StudySheetError):
            return {"job_id": job_id, "status": "failed", "error": message}
        return {"job_id": job_id, "status": "failed", "error": message}


def _total_cost(
    provider: str,
    model: str,
    usages: list[dict[str, int]],
) -> float:
    total = 0.0
    for usage in usages:
        priced = cost_llm_usage(
            provider=provider,
            model=model,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
        )
        total += float(priced.get("cost_usd") or 0)
    return round(total, 6)
