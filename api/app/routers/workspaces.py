from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.dependencies.auth import require_approved_user
from app.dependencies.services import (
    get_stage_settings_repository,
    get_workspace_repository,
)
from app.dependencies.workspace import require_workspace
from app.llm_actions import LLM_ACTIONS
from app.models.auth import CurrentUser
from app.models.stage_settings import (
    StageSetting,
    StageSettingsResponse,
    StageSettingUpdate,
)
from app.models.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from app.repositories.stage_settings import StageSettingsRepository
from app.repositories.workspaces import WorkspaceRepository
from app.services.llm.model_catalog import validate_selection

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

_STAGE_ACTION_LABELS: dict[str, str] = {action.key: action.label for action in LLM_ACTIONS}


def _default_provider_model(stage_action: str) -> tuple[str, str]:
    resolved = get_settings().llm.resolve_action(stage_action)
    return resolved.provider, resolved.model


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> list[WorkspaceResponse]:
    rows = await workspaces.list_for_owner(user.id)
    return [WorkspaceResponse.model_validate(row) for row in rows]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> WorkspaceResponse:
    row = await workspaces.create(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
    )
    return WorkspaceResponse.model_validate(row)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
) -> WorkspaceResponse:
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    payload: WorkspaceUpdate,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> WorkspaceResponse:
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        return workspace

    row = await workspaces.update(workspace.id, user.id, updates)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return WorkspaceResponse.model_validate(row)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    workspaces: Annotated[WorkspaceRepository, Depends(get_workspace_repository)],
) -> None:
    await workspaces.delete(workspace.id, user.id)


@router.get("/{workspace_id}/stage-settings", response_model=StageSettingsResponse)
async def get_stage_settings(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    stage_settings: Annotated[
        StageSettingsRepository,
        Depends(get_stage_settings_repository),
    ],
) -> StageSettingsResponse:
    stored = {
        str(row["stage_action"]): row
        for row in await stage_settings.list_for_workspace(workspace.id)
    }

    settings: list[StageSetting] = []
    for action in LLM_ACTIONS:
        default_provider, default_model = _default_provider_model(action.key)
        row = stored.get(action.key)

        settings.append(
            StageSetting(
                stage_action=action.key,
                label=action.label,
                provider=str(row["provider"]) if row else default_provider,
                model=str(row["model"]) if row else default_model,
                reasoning_effort=row.get("reasoning_effort") if row else None,
                reasoning_tokens=row.get("reasoning_tokens") if row else None,
                is_overridden=row is not None,
                default_provider=default_provider,
                default_model=default_model,
            ),
        )

    return StageSettingsResponse(settings=settings)


@router.put("/{workspace_id}/stage-settings/{stage_action}", response_model=StageSetting)
async def put_stage_setting(
    stage_action: str,
    payload: StageSettingUpdate,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    stage_settings: Annotated[
        StageSettingsRepository,
        Depends(get_stage_settings_repository),
    ],
) -> StageSetting:
    if stage_action not in _STAGE_ACTION_LABELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown stage action '{stage_action}'.",
        )

    error = validate_selection(payload.provider, payload.model)
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )

    reasoning_effort = payload.reasoning_effort.strip().lower() if payload.reasoning_effort else None

    row = await stage_settings.upsert(
        workspace_id=workspace.id,
        stage_action=stage_action,
        provider=payload.provider.strip().lower(),
        model=payload.model.strip(),
        reasoning_effort=reasoning_effort or None,
        reasoning_tokens=payload.reasoning_tokens,
    )

    default_provider, default_model = _default_provider_model(stage_action)

    return StageSetting(
        stage_action=stage_action,
        label=_STAGE_ACTION_LABELS[stage_action],
        provider=str(row["provider"]),
        model=str(row["model"]),
        reasoning_effort=row.get("reasoning_effort"),
        reasoning_tokens=row.get("reasoning_tokens"),
        is_overridden=True,
        default_provider=default_provider,
        default_model=default_model,
    )


@router.delete(
    "/{workspace_id}/stage-settings/{stage_action}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_stage_setting(
    stage_action: str,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    stage_settings: Annotated[
        StageSettingsRepository,
        Depends(get_stage_settings_repository),
    ],
) -> None:
    if stage_action not in _STAGE_ACTION_LABELS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown stage action '{stage_action}'.",
        )

    await stage_settings.delete(workspace_id=workspace.id, stage_action=stage_action)
