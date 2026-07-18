from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import (
    get_source_repository,
    get_wiki_authoring_service,
    get_wiki_entry_repository,
)
from app.dependencies.workspace import require_workspace
from app.models.auth import CurrentUser
from app.models.wiki_entry import (
    WikiDisputeResponse,
    WikiEntryCreate,
    WikiEntryResponse,
    WikiEntryUpdate,
)
from app.models.wiki_ingest import (
    WikiIngestBatchResponse,
    WikiIngestBatchUpdate,
    WikiIngestCommitResponse,
    WikiIngestCreate,
    batch_row_to_response,
)
from app.models.workspace import WorkspaceResponse
from app.repositories.sources import SourceRepository
from app.repositories.wiki_entries import WikiEntryRepository
from app.services.wiki_authoring import (
    WikiAuthoringError,
    WikiAuthoringService,
    WikiIngestDriftError,
    WikiIngestNotFoundError,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/wiki", tags=["wiki"])


@router.get("/entries", response_model=list[WikiEntryResponse])
async def list_wiki_entries(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    wiki_entries: Annotated[WikiEntryRepository, Depends(get_wiki_entry_repository)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WikiEntryResponse]:
    rows = await wiki_entries.list_for_workspace(
        workspace.id,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return [WikiEntryResponse.model_validate(row) for row in rows]


@router.post(
    "/entries",
    response_model=WikiEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wiki_entry(
    payload: WikiEntryCreate,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiEntryResponse:
    try:
        row = await authoring.create_entry(
            workspace.id,
            preferred_label=payload.preferred_label,
            definition=payload.definition,
            entry_kind=payload.entry_kind,
            importance=payload.importance,
            aliases=payload.aliases,
            pronunciation=payload.pronunciation,
        )
    except WikiAuthoringError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return WikiEntryResponse.model_validate(row)


@router.get("/entries/{wiki_entry_id}", response_model=WikiEntryResponse)
async def get_wiki_entry(
    wiki_entry_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    wiki_entries: Annotated[WikiEntryRepository, Depends(get_wiki_entry_repository)],
) -> WikiEntryResponse:
    row = await wiki_entries.get_for_workspace(wiki_entry_id, workspace.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wiki entry not found.",
        )

    return WikiEntryResponse.model_validate(row)


@router.patch("/entries/{wiki_entry_id}", response_model=WikiEntryResponse)
async def update_wiki_entry(
    wiki_entry_id: str,
    payload: WikiEntryUpdate,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiEntryResponse:
    updates = payload.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    try:
        row = await authoring.update_entry(wiki_entry_id, workspace.id, updates)
    except WikiIngestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return WikiEntryResponse.model_validate(row)


@router.delete("/entries/{wiki_entry_id}", response_model=WikiEntryResponse)
async def deprecate_wiki_entry(
    wiki_entry_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiEntryResponse:
    """Soft delete: canonical → deprecated (QnGen and the assistant filter it out)."""
    try:
        row = await authoring.deprecate_entry(wiki_entry_id, workspace.id)
    except WikiIngestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return WikiEntryResponse.model_validate(row)


@router.get("/disputes", response_model=list[WikiDisputeResponse])
async def list_wiki_disputes(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    wiki_entries: Annotated[WikiEntryRepository, Depends(get_wiki_entry_repository)],
    status_filter: Annotated[str | None, Query(alias="status")] = "open",
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[WikiDisputeResponse]:
    rows = await wiki_entries.list_disputes_for_workspace(
        workspace.id,
        status=status_filter,
        limit=limit,
    )
    return [WikiDisputeResponse.model_validate(row) for row in rows]


# ---------------------------------------------------------------------------
# Ingest batches: notes dump → structured draft → review → commit
# ---------------------------------------------------------------------------


@router.post(
    "/ingest-batches",
    response_model=WikiIngestBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ingest_batch(
    payload: WikiIngestCreate,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    sources: Annotated[SourceRepository, Depends(get_source_repository)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiIngestBatchResponse:
    if payload.source_id:
        found = await sources.get_many_for_workspace(
            [payload.source_id],
            workspace.id,
            user.id,
        )

        if not found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_id is invalid for this workspace.",
            )

    try:
        row = await authoring.create_batch(payload, workspace.id)
    except WikiAuthoringError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return batch_row_to_response(row)


@router.get("/ingest-batches", response_model=list[WikiIngestBatchResponse])
async def list_ingest_batches(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[WikiIngestBatchResponse]:
    rows = await authoring.batches.list_for_workspace(
        workspace.id,
        status=status_filter,
        limit=limit,
    )
    return [batch_row_to_response(row) for row in rows]


@router.get("/ingest-batches/{batch_id}", response_model=WikiIngestBatchResponse)
async def get_ingest_batch(
    batch_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiIngestBatchResponse:
    row = await authoring.batches.get_for_workspace(batch_id, workspace.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingest batch not found.",
        )

    return batch_row_to_response(row)


@router.patch("/ingest-batches/{batch_id}", response_model=WikiIngestBatchResponse)
async def update_ingest_batch(
    batch_id: str,
    payload: WikiIngestBatchUpdate,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiIngestBatchResponse:
    try:
        row = await authoring.update_batch(
            batch_id,
            workspace.id,
            title=payload.title,
            entries=payload.entries,
        )
    except WikiIngestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WikiAuthoringError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return batch_row_to_response(row)


@router.post("/ingest-batches/{batch_id}/commit", response_model=WikiIngestCommitResponse)
async def commit_ingest_batch(
    batch_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiIngestCommitResponse:
    try:
        batch, inserted_ids, updated_ids = await authoring.commit_batch(batch_id, workspace.id)
    except WikiIngestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WikiAuthoringError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WikiIngestDriftError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": str(exc),
                "drifted_indexes": exc.drifted_indexes,
                "batch": batch_row_to_response(exc.batch).model_dump(mode="json"),
            },
        ) from exc

    return WikiIngestCommitResponse(
        batch=batch_row_to_response(batch),
        inserted_entry_ids=inserted_ids,
        updated_entry_ids=updated_ids,
    )


@router.post("/ingest-batches/{batch_id}/discard", response_model=WikiIngestBatchResponse)
async def discard_ingest_batch(
    batch_id: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    authoring: Annotated[WikiAuthoringService, Depends(get_wiki_authoring_service)],
) -> WikiIngestBatchResponse:
    try:
        row = await authoring.discard_batch(batch_id, workspace.id)
    except WikiIngestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WikiAuthoringError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return batch_row_to_response(row)
