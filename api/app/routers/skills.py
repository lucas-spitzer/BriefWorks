from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.auth import require_approved_user
from app.dependencies.services import get_skill_repository
from app.models.auth import CurrentUser
from app.models.skill import SkillResponse
from app.repositories.skills import SkillRepository

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillResponse])
async def list_skills(
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    skills: Annotated[SkillRepository, Depends(get_skill_repository)],
    module: Annotated[str | None, Query(pattern="^(intellex|mathesys|qngen)$")] = None,
) -> list[SkillResponse]:
    rows = await skills.list_active(module=module)
    return [SkillResponse.model_validate(row) for row in rows]


@router.get("/{skill_id}/{version}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    version: str,
    _: Annotated[CurrentUser, Depends(require_approved_user)],
    skills: Annotated[SkillRepository, Depends(get_skill_repository)],
) -> SkillResponse:
    row = await skills.get(skill_id, version)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found.",
        )

    return SkillResponse.model_validate(row)
