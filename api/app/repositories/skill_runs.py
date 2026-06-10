from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class SkillRunRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.insert("skill_runs", payload)
        return rows[0]

    async def get(self, skill_run_id: str) -> dict[str, Any] | None:
        return await self.db.select_one(
            "skill_runs",
            filters={"id": f"eq.{skill_run_id}"},
        )

    async def list_for_workspace(
        self,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "skill_runs",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
        )

    async def list_for_production_run(
        self,
        production_run_id: str,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "skill_runs",
            filters={"production_run_id": f"eq.{production_run_id}"},
            order="created_at.asc",
        )

    async def update(
        self,
        skill_run_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        rows = await self.db.update(
            "skill_runs",
            filters={"id": f"eq.{skill_run_id}"},
            payload=payload,
        )
        return rows[0] if rows else None
