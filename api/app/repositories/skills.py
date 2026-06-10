from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class SkillRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_active(self, *, module: str | None = None) -> list[dict[str, Any]]:
        filters: dict[str, str] = {"is_active": "eq.true"}

        if module:
            filters["module"] = f"eq.{module}"

        return await self.db.select_many(
            "skills",
            filters=filters,
            order="module.asc,skill_id.asc,version.desc",
        )

    async def get(self, skill_id: str, version: str) -> dict[str, Any] | None:
        return await self.db.select_one(
            "skills",
            filters={
                "skill_id": f"eq.{skill_id}",
                "version": f"eq.{version}",
            },
        )
