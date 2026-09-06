"""Create standalone study-sheet generate jobs from an uploaded file."""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from app.artifact_paths import next_available_slug, original_path, slug_from_filename
from app.config import Settings, get_settings
from app.mathesys.study_sheet.upload import (
    StudySheetUploadError,
    validate_study_sheet_upload,
)
from app.models.workspace import WorkspaceResponse
from app.repositories.sources import SourceRepository
from app.repositories.study_sheet_jobs import StudySheetJobRepository
from app.services.queue import enqueue_study_sheet_job
from app.services.supabase_storage import SupabaseStorageClient

logger = logging.getLogger(__name__)


class StudySheetEnqueueError(Exception):
    """Raised when the study-sheet job cannot be queued."""


class StudySheetService:
    def __init__(
        self,
        *,
        jobs: StudySheetJobRepository,
        sources: SourceRepository,
        storage: SupabaseStorageClient,
        settings: Settings | None = None,
    ) -> None:
        self.jobs = jobs
        self.sources = sources
        self.storage = storage
        self.settings = settings or get_settings()

    async def create_job(
        self,
        *,
        workspace: WorkspaceResponse,
        owner_id: str,
        filename: str | None,
        content_type: str | None,
        content: bytes,
    ) -> dict[str, Any]:
        sheet_settings = self.settings.study_sheet
        safe_filename, mime_type = validate_study_sheet_upload(
            filename=filename,
            content_type=content_type,
            content=content,
            max_bytes=sheet_settings.max_upload_bytes,
            max_markdown_chars=sheet_settings.max_markdown_chars,
        )
        file_hash = hashlib.sha256(content).hexdigest()
        source = await self._source_for_upload(
            workspace=workspace,
            owner_id=owner_id,
            filename=safe_filename,
            mime_type=mime_type,
            content=content,
            file_hash=file_hash,
        )
        job = await self.jobs.insert(
            {
                "workspace_id": workspace.id,
                "source_id": source["id"],
                "status": "queued",
                "input_filename": safe_filename,
                "input_mime_type": mime_type,
                "input_storage_path": source["storage_path"],
                "input_file_size_bytes": len(content),
            },
        )
        try:
            enqueue_study_sheet_job(self.settings, str(job["id"]))
        except Exception as exc:
            await self.jobs.update(
                str(job["id"]),
                {
                    "status": "failed",
                    "error": f"Failed to enqueue study sheet job: {exc}",
                },
            )
            raise StudySheetEnqueueError(
                "Study sheet could not be queued. Is Redis running?",
            ) from exc

        return job

    async def _source_for_upload(
        self,
        *,
        workspace: WorkspaceResponse,
        owner_id: str,
        filename: str,
        mime_type: str,
        content: bytes,
        file_hash: str,
    ) -> dict[str, Any]:
        existing = await self.sources.get_by_hash(workspace.id, file_hash)
        if existing:
            return existing

        taken = await self.sources.list_slugs_for_workspace(workspace.id)
        slug = next_available_slug(slug_from_filename(filename), taken)
        storage_path = original_path(workspace.slug, slug, filename)
        await self.storage.upload(
            bucket=self.settings.sources_bucket,
            path=storage_path,
            content=content,
            content_type=mime_type,
            upsert=False,
        )
        try:
            return await self.sources.create(
                {
                    "id": str(uuid.uuid4()),
                    "workspace_id": workspace.id,
                    "owner_id": owner_id,
                    "filename": filename,
                    "slug": slug,
                    "mime_type": mime_type,
                    "storage_path": storage_path,
                    "file_hash": file_hash,
                    "file_size_bytes": len(content),
                    "status": "stored",
                },
            )
        except Exception:
            try:
                await self.storage.delete(
                    bucket=self.settings.sources_bucket,
                    path=storage_path,
                )
            except Exception:
                logger.exception(
                    "Failed to delete orphaned study-sheet source at %s",
                    storage_path,
                )
            raise
