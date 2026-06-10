from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_workspace_repository
from app.models.auth import CurrentUser
from app.repositories.workspaces import WorkspaceRepository


async def require_workspace(
    workspace_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> dict:
    workspace = await workspaces.get_for_owner(workspace_id, user.id)

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return workspace
