from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_workspace_repository
from app.dependencies.workspace import require_workspace
from app.models.auth import CurrentUser
from app.models.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from app.repositories.workspaces import WorkspaceRepository
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> list[WorkspaceResponse]:
    try:
        rows = await workspaces.list_for_owner(user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [WorkspaceResponse.model_validate(row) for row in rows]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> WorkspaceResponse:
    try:
        row = await workspaces.create(
            owner_id=user.id,
            name=payload.name,
            description=payload.description,
        )
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return WorkspaceResponse.model_validate(row)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace: Annotated[dict, Depends(require_workspace)],
) -> WorkspaceResponse:
    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    payload: WorkspaceUpdate,
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> WorkspaceResponse:
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        return WorkspaceResponse.model_validate(workspace)

    try:
        row = await workspaces.update(workspace["id"], user.id, updates)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return WorkspaceResponse.model_validate(row)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace: Annotated[dict, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> None:
    try:
        await workspaces.delete(workspace["id"], user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
