import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.config import Settings, get_settings
from app.dependencies.auth import require_approved_user
from app.dependencies.services import (
    get_ndr_segment_repository,
    get_source_repository,
    get_supabase_storage_client,
)
from app.dependencies.workspace import require_workspace
from app.models.auth import CurrentUser
from app.models.ndr_segment import NdrSegmentResponse
from app.models.source import SourceResponse
from app.repositories.ndr_segments import NdrSegmentRepository
from app.repositories.sources import SourceRepository
from app.services.supabase_rest import SupabaseRestError
from app.services.supabase_storage import SupabaseStorageClient, SupabaseStorageError

router = APIRouter(prefix="/workspaces/{workspace_id}/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
) -> list[SourceResponse]:
    try:
        rows = await sources.list_for_workspace(workspace["id"], user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [SourceResponse.model_validate(row) for row in rows]


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_source(
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
    storage: Annotated[SupabaseStorageClient, Depends(get_supabase_storage_client)],
    file: UploadFile = File(...),
) -> SourceResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must include a filename.",
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    mime_type = file.content_type or "application/octet-stream"
    file_hash = hashlib.sha256(content).hexdigest()
    source_id = str(uuid.uuid4())
    storage_path = (
        f"workspaces/{workspace['id']}/sources/{source_id}/{file.filename}"
    )

    try:
        await storage.upload(
            bucket=settings.sources_bucket,
            path=storage_path,
            content=content,
            content_type=mime_type,
            upsert=False,
        )
    except SupabaseStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    try:
        row = await sources.create(
            {
                "id": source_id,
                "workspace_id": workspace["id"],
                "owner_id": user.id,
                "filename": file.filename,
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
        except SupabaseStorageError:
            pass

        if "duplicate key value" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This file has already been uploaded to the workspace.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return SourceResponse.model_validate(row)


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
) -> SourceResponse:
    try:
        row = await sources.get_for_workspace(source_id, workspace["id"], user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    return SourceResponse.model_validate(row)


@router.get("/{source_id}/segments", response_model=list[NdrSegmentResponse])
async def list_source_segments(
    source_id: str,
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    segments: Annotated[NdrSegmentRepository, Depends(get_ndr_segment_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[NdrSegmentResponse]:
    try:
        rows = await segments.list_for_source(
            source_id,
            workspace["id"],
            user.id,
            limit=limit,
            offset=offset,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        ) from exc
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [NdrSegmentResponse.model_validate(row) for row in rows]


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    source_id: str,
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
    storage: Annotated[SupabaseStorageClient, Depends(get_supabase_storage_client)],
) -> None:
    try:
        row = await sources.delete(source_id, workspace["id"], user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    try:
        await storage.delete(
            bucket=settings.sources_bucket,
            path=row["storage_path"],
        )
    except SupabaseStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
