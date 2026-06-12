from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_wiki_entry_repository
from app.dependencies.workspace import require_workspace
from app.models.auth import CurrentUser
from app.models.wiki_entry import WikiDisputeResponse, WikiEntryResponse
from app.models.workspace import WorkspaceResponse
from app.repositories.wiki_entries import WikiEntryRepository

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
