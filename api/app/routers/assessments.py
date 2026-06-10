from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_assessment_repository
from app.dependencies.workspace import require_workspace
from app.models.assessment import FlashcardResponse, QuizResponse, ScenarioResponse
from app.models.auth import CurrentUser
from app.repositories.assessments import AssessmentRepository
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(tags=["assessments"])


@router.get(
    "/workspaces/{workspace_id}/flashcards",
    response_model=list[FlashcardResponse],
)
async def list_flashcards(
    workspace: Annotated[dict, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[FlashcardResponse]:
    try:
        rows = await assessments.list_flashcards(
            workspace["id"],
            limit=limit,
            offset=offset,
        )
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [FlashcardResponse.model_validate(row) for row in rows]


@router.get("/flashcards/{flashcard_id}", response_model=FlashcardResponse)
async def get_flashcard(
    flashcard_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
) -> FlashcardResponse:
    try:
        row = await assessments.get_flashcard_for_owner(flashcard_id, user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

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
    workspace: Annotated[dict, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[QuizResponse]:
    try:
        rows = await assessments.list_quizzes(
            workspace["id"],
            limit=limit,
            offset=offset,
        )
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [QuizResponse.model_validate(row) for row in rows]


@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
async def get_quiz(
    quiz_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
) -> QuizResponse:
    try:
        row = await assessments.get_quiz_for_owner(quiz_id, user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

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
    workspace: Annotated[dict, Depends(require_workspace)],
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScenarioResponse]:
    try:
        rows = await assessments.list_scenarios(
            workspace["id"],
            limit=limit,
            offset=offset,
        )
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [ScenarioResponse.model_validate(row) for row in rows]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: str,
    user: Annotated[CurrentUser, Depends(require_approved_user)],
    assessments: Annotated[AssessmentRepository, Depends(get_assessment_repository)],
) -> ScenarioResponse:
    try:
        row = await assessments.get_scenario_for_owner(scenario_id, user.id)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    return ScenarioResponse.model_validate(row)
