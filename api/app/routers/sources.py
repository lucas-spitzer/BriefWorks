import hashlib
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.config import Settings, get_settings
from app.dependencies.auth import require_approved_user
from app.dependencies.services import (
    get_ndr_segment_repository,
    get_production_run_repository,
    get_source_repository,
    get_supabase_storage_client,
)
from app.dependencies.workspace import require_workspace
from app.errors import is_duplicate_key_error
from app.models.auth import CurrentUser
from app.models.ndr_segment import NdrSegmentResponse
from app.models.source import SourceResponse
from app.models.workspace import WorkspaceResponse
from app.repositories.ndr_segments import NdrSegmentRepository
from app.repositories.production_runs import ProductionRunRepository
from app.repositories.sources import SourceRepository
from app.services.production_runs import ProductionRunEnqueueError, create_and_enqueue_production_run
from app.services.source_upload import SourceUploadValidationError, validate_source_upload
from app.services.supabase_rest import SupabaseRestError
from app.services.supabase_storage import SupabaseStorageClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces/{workspace_id}/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
) -> list[SourceResponse]:
    rows = await sources.list_for_workspace(workspace.id, user.id)
    return [SourceResponse.model_validate(row) for row in rows]


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
    production_runs: Annotated[ProductionRunRepository, Depends(get_production_run_repository)],
    storage: Annotated[SupabaseStorageClient, Depends(get_supabase_storage_client)],
    file: UploadFile = File(...),
) -> SourceResponse:
    content = await file.read()

    try:
        safe_filename, mime_type = validate_source_upload(
            filename=file.filename,
            content_type=file.content_type,
            content=content,
            max_bytes=settings.max_source_upload_bytes,
        )
    except SourceUploadValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    file_hash = hashlib.sha256(content).hexdigest()
    source_id = str(uuid.uuid4())
    storage_path = f"workspaces/{workspace.id}/sources/{source_id}/{safe_filename}"

    await storage.upload(
        bucket=settings.sources_bucket,
        path=storage_path,
        content=content,
        content_type=mime_type,
        upsert=False,
    )

    try:
        row = await sources.create(
            {
                "id": source_id,
                "workspace_id": workspace.id,
                "owner_id": user.id,
                "filename": safe_filename,
                "mime_type": mime_type,
                "storage_path": storage_path,
                "file_hash": file_hash,
                "file_size_bytes": len(content),
                "status": "stored",
            },
        )
    except SupabaseRestError as exc:
        try:
            await storage.delete(
                bucket=settings.sources_bucket,
                path=storage_path,
            )
        except Exception:
            logger.exception(
                "Failed to delete orphaned source upload at %s after DB error",
                storage_path,
            )

        if is_duplicate_key_error(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This file has already been uploaded to the workspace.",
            ) from exc

        raise

    try:
        await create_and_enqueue_production_run(
            workspace_id=workspace.id,
            owner_id=user.id,
            source_ids=[source_id],
            target_artifacts=[],
            settings=settings,
            production_runs=production_runs,
        )
    except ProductionRunEnqueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Source uploaded but ingest could not be queued. Is Redis running?",
        ) from exc

    return SourceResponse.model_validate(row)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
) -> SourceResponse:
    row = await sources.get_for_workspace(source_id, workspace.id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    return SourceResponse.model_validate(row)


@router.get("/{source_id}/segments", response_model=list[NdrSegmentResponse])
async def list_source_segments(
    source_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    segments: Annotated[NdrSegmentRepository, Depends(get_ndr_segment_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NdrSegmentResponse]:
    try:
        rows = await segments.list_for_source(
            source_id,
            workspace.id,
            user.id,
            limit=limit,
            offset=offset,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        ) from exc

    return [NdrSegmentResponse.model_validate(row) for row in rows]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
    storage: Annotated[SupabaseStorageClient, Depends(get_supabase_storage_client)],
) -> None:
    row = await sources.delete(source_id, workspace.id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    await storage.delete(
        bucket=settings.sources_bucket,
        path=row["storage_path"],
    )
