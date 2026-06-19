from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class StageRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_active(self, *, module: str | None = None) -> list[dict[str, Any]]:
        filters: dict[str, str] = {"is_active": "eq.true"}

        if module:
            filters["module"] = f"eq.{module}"

        return await self.db.select_many(
            "stages",
            filters=filters,
            order="module.asc,stage_id.asc,version.desc",
        )

    async def get(self, stage_id: str, version: str) -> dict[str, Any] | None:
        return await self.db.select_one(
            "stages",
            filters={
                "stage_id": f"eq.{stage_id}",
                "version": f"eq.{version}",
            },
        )
