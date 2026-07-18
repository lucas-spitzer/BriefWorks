from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_assistant_service
from app.dependencies.workspace import require_workspace
from app.models.assistant import AssistantChatRequest, AssistantChatResponse
from app.models.auth import CurrentUser
from app.models.workspace import WorkspaceResponse
from app.services.assistant import AssistantService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/assistant",
    tags=["assistant"],
)


@router.post("/chat", response_model=AssistantChatResponse)
async def assistant_chat(
    request: AssistantChatRequest,
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assistant: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantChatResponse:
    return await assistant.chat(request, workspace.id)
