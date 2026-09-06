from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.config import Settings, get_settings
from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_study_sheet_service
from app.dependencies.workspace import require_workspace
from app.mathesys.study_sheet.upload import StudySheetUploadError
from app.models.auth import CurrentUser
from app.models.study_sheet import StudySheetJobResponse, job_row_to_response
from app.models.workspace import WorkspaceResponse
from app.services.study_sheet import StudySheetEnqueueError, StudySheetService

router = APIRouter(tags=["study-sheets"])


@router.get(
    "/workspaces/{workspace_id}/study-sheets",
    response_model=list[StudySheetJobResponse],
)
async def list_study_sheet_jobs(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    service: Annotated[StudySheetService, Depends(get_study_sheet_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StudySheetJobResponse]:
    rows = await service.jobs.list_for_workspace(
        workspace.id,
        limit=limit,
        offset=offset,
    )
    return [job_row_to_response(row) for row in rows]


@router.post(
    "/workspaces/{workspace_id}/study-sheets",
    response_model=StudySheetJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_study_sheet_job(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[StudySheetService, Depends(get_study_sheet_service)],
    file: UploadFile = File(...),
) -> StudySheetJobResponse:
    max_bytes = settings.study_sheet.max_upload_bytes
    content = await file.read(max_bytes + 1)
    try:
        row = await service.create_job(
            workspace=workspace,
            owner_id=user.id,
            filename=file.filename,
            content_type=file.content_type,
            content=content,
        )
    except StudySheetUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except StudySheetEnqueueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return job_row_to_response(row)
