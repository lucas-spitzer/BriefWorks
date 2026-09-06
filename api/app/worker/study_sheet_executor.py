"""Mathesys stage: compress a library source into a one- or two-page PDF."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.artifact_paths import OUTPUT_FILENAMES, downloadable_artifact_path
from app.config import get_settings
from app.mathesys.study_sheet.generate import (
    StudySheetResult,
    StudySheetSource,
    generate_study_sheet,
)
from app.mathesys.study_sheet.printer import WeasyPrintPdfPrinter
from app.services.llm import get_llm_client
from app.services.stage_run_billing import stage_run_completion_fields
from app.worker.db import WorkerDatabase
from app.worker.storage import WorkerStorage

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def summed_token_usage(usages: list[dict[str, int]]) -> dict[str, int]:
    input_tokens = sum(int(usage.get("input_tokens") or 0) for usage in usages)
    output_tokens = sum(int(usage.get("output_tokens") or 0) for usage in usages)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


class CreateStudySheetStageExecutor:
    STAGE_ID = "generate-study-sheet"
    STAGE_VERSION = "1.0"
    MODULE = "mathesys"

    def __init__(
        self,
        db: WorkerDatabase | None = None,
        storage: WorkerStorage | None = None,
    ) -> None:
        self.db = db or WorkerDatabase()
        self.storage = storage or WorkerStorage()

    def run_for_source(
        self,
        *,
        production_run_id: str,
        workspace_id: str,
        source: dict[str, Any],
    ) -> str:
        source_id = source["id"]
        storage_path = str(source.get("storage_path") or "")
        if not storage_path:
            raise RuntimeError(f"Source {source_id} has no original file.")

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
                },
                "started_at": utc_now_iso(),
            },
        )
        stage_run_id = stage_run["id"]

        try:
            settings = get_settings()
            content = self.storage.download(storage_path)
            result = generate_study_sheet(
                source=StudySheetSource(
                    filename=str(source.get("filename") or "source"),
                    mime_type=str(source.get("mime_type") or ""),
                    content=content,
                ),
                completer=get_llm_client("study_sheet"),
                printer=WeasyPrintPdfPrinter(),
                max_attempts=settings.study_sheet.max_attempts,
            )
            artifact = self._write_artifact(
                source=source,
                workspace_id=workspace_id,
                production_run_id=production_run_id,
                stage_run_id=stage_run_id,
                result=result,
            )
            execution = {
                "model": result.model,
                "provider": result.provider,
                "token_usage": summed_token_usage(result.token_usages),
            }
            self.db.update_stage_run(
                stage_run_id,
                {
                    "status": "completed",
                    "output": {
                        "files": [
                            {
                                "artifact_id": artifact["id"],
                                "filename": artifact["filename"],
                                "storage_path": artifact["storage_path"],
                            },
                        ],
                        "title": result.title,
                        "page_count": result.page_count,
                        "attempts": result.attempt_count,
                    },
                    "promoted": {"artifact_ids": [artifact["id"]]},
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

    def _write_artifact(
        self,
        *,
        source: dict[str, Any],
        workspace_id: str,
        production_run_id: str,
        stage_run_id: str,
        result: StudySheetResult,
    ) -> dict[str, Any]:
        filename = OUTPUT_FILENAMES["study_sheet"]
        storage_path = downloadable_artifact_path(source, "study_sheet")
        self.storage.upload(storage_path, result.pdf, content_type="application/pdf")
        payload = {
            "workspace_id": workspace_id,
            "source_id": source["id"],
            "production_run_id": production_run_id,
            "artifact_type": "study_sheet",
            "format": "pdf",
            "filename": filename,
            "storage_path": storage_path,
            "file_size_bytes": len(result.pdf),
            "manifest": {
                "module": "mathesys",
                "title": result.title,
                "page_count": result.page_count,
                "attempts": result.attempt_count,
            },
            "origin": {
                "stage_run_id": stage_run_id,
                "stage_id": self.STAGE_ID,
                "stage_version": self.STAGE_VERSION,
                "model": result.model,
                "provider": result.provider,
            },
        }
        existing = self.db.list_artifacts_for_source(
            source["id"],
            artifact_type="study_sheet",
        )
        if existing:
            return self.db.update_artifact(existing[0]["id"], payload)
        return self.db.create_artifact(payload)
