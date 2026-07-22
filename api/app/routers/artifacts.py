from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import Settings, get_settings
from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_artifact_repository, get_supabase_storage_client
from app.dependencies.workspace import require_workspace
from app.models.artifact import ArtifactDownloadResponse, ArtifactResponse
from app.models.auth import CurrentUser
from app.models.workspace import WorkspaceResponse
from app.repositories.artifacts import ArtifactRepository
from app.services.supabase_storage import SupabaseStorageClient

router = APIRouter(tags=["artifacts"])


@router.get(
    "/workspaces/{workspace_id}/artifacts",
    response_model=list[ArtifactResponse],
)
async def list_artifacts(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    artifacts: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    artifact_type: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ArtifactResponse]:
    rows = await artifacts.list_for_workspace(
        workspace.id,
        artifact_type=artifact_type,
        limit=limit,
        offset=offset,
    )
    return [ArtifactResponse.model_validate(row) for row in rows]


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    artifacts: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
) -> ArtifactResponse:
    row = await artifacts.get_for_owner(artifact_id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found.",
        )

    return ArtifactResponse.model_validate(row)


@router.get("/artifacts/{artifact_id}/download", response_model=ArtifactDownloadResponse)
async def download_artifact(
    artifact_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    artifacts: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
    storage: Annotated[SupabaseStorageClient, Depends(get_supabase_storage_client)],
) -> ArtifactDownloadResponse:
    row = await artifacts.get_for_owner(artifact_id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Artifact not found.",
        )

    download_url = await storage.create_signed_url(
        bucket=settings.sources_bucket,
        path=row["storage_path"],
        expires_in=settings.signed_url_expires_seconds,
    )

    return ArtifactDownloadResponse(
        artifact_id=artifact_id,
        filename=row["filename"],
        download_url=download_url,
        expires_in=settings.signed_url_expires_seconds,
    )
