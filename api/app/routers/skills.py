from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_skill_repository
from app.models.auth import CurrentUser
from app.models.skill import SkillResponse
from app.repositories.skills import SkillRepository
from app.services.supabase_rest import SupabaseRestError

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
async def list_skills(
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    skills: Annotated[SkillRepository, Depends(get_skill_repository)],
    module: Annotated[str | None, Query(pattern="^(intellex|mathesys|qngen)$")] = None,
) -> list[SkillResponse]:
    try:
        rows = await skills.list_active(module=module)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return [SkillResponse.model_validate(row) for row in rows]


@router.get("/{skill_id}/{version}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    version: str,
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    skills: Annotated[SkillRepository, Depends(get_skill_repository)],
) -> SkillResponse:
    try:
        row = await skills.get(skill_id, version)
    except SupabaseRestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    return SkillResponse.model_validate(row)
