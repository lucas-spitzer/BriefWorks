from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_assessment_repository
from app.dependencies.workspace import require_workspace
from app.models.assessment import (
    FlashcardResponse,
    QuizResponse,
    ScenarioResponse,
)
from app.models.auth import CurrentUser
from app.models.workspace import WorkspaceResponse
from app.repositories.assessments import AssessmentRepository

router = APIRouter(tags=["assessments"])


@router.get(
    "/workspaces/{workspace_id}/flashcards",
    response_model=list[FlashcardResponse],
)
async def list_flashcards(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FlashcardResponse]:
    rows = await assessments.list_flashcards(
        workspace.id,
        limit=limit,
        offset=offset,
    )
    return [FlashcardResponse.model_validate(row) for row in rows]


@router.get("/flashcards/{flashcard_id}", response_model=FlashcardResponse)
async def get_flashcard(
    flashcard_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
) -> FlashcardResponse:
    row = await assessments.get_flashcard_for_owner(flashcard_id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flashcard not found.",
        )

    return FlashcardResponse.model_validate(row)


@router.get(
    "/workspaces/{workspace_id}/quizzes",
    response_model=list[QuizResponse],
)
async def list_quizzes(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[QuizResponse]:
    rows = await assessments.list_quizzes(
        workspace.id,
        limit=limit,
        offset=offset,
    )
    return [QuizResponse.model_validate(row) for row in rows]


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
) -> QuizResponse:
    row = await assessments.get_quiz_for_owner(quiz_id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz question not found.",
        )

    return QuizResponse.model_validate(row)


@router.get(
    "/workspaces/{workspace_id}/scenarios",
    response_model=list[ScenarioResponse],
)
async def list_scenarios(
    workspace: Annotated[WorkspaceResponse, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScenarioResponse]:
    rows = await assessments.list_scenarios(
        workspace.id,
        limit=limit,
        offset=offset,
    )
    return [ScenarioResponse.model_validate(row) for row in rows]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
) -> ScenarioResponse:
    row = await assessments.get_scenario_for_owner(scenario_id, user.id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    return ScenarioResponse.model_validate(row)
