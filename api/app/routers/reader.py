from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import require_approved_user
from app.dependencies.workspace import require_workspace
from app.models.auth import CurrentUser
from app.models.reader_define import ReaderDefineRequest, ReaderDefineResponse
from app.models.workspace import WorkspaceResponse
from app.services.reader_define import (
    ReaderDefineError,
    ReaderDefineService,
    get_reader_define_service,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/reader", tags=["reader"])


@router.post("/define", response_model=ReaderDefineResponse)
async def define_reader_term(
    request: ReaderDefineRequest,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    service: Annotated[ReaderDefineService, Depends(get_reader_define_service)],
) -> ReaderDefineResponse:
    del workspace  # auth/ownership already enforced by require_workspace
    try:
        return await service.define(request)
    except ReaderDefineError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
