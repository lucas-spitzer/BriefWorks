from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class StageRunRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.insert("stage_runs", payload)
        return rows[0]

    async def get(self, stage_run_id: str) -> dict[str, Any] | None:
        return await self.db.select_one(
            "stage_runs",
            filters={"id": f"eq.{stage_run_id}"},
        )

    async def list_for_workspace(
        self,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "stage_runs",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
        )

    async def list_for_production_run(
        self,
        production_run_id: str,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "stage_runs",
            filters={"production_run_id": f"eq.{production_run_id}"},
            order="created_at.asc",
        )

    async def update(
        self,
        stage_run_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        rows = await self.db.update(
            "stage_runs",
            filters={"id": f"eq.{stage_run_id}"},
            payload=payload,
        )
        return rows[0] if rows else None
