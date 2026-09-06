from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class StudySheetJobRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_for_workspace(
        self,
        workspace_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "study_sheet_jobs",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

    async def get_for_workspace(
        self,
        job_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "study_sheet_jobs",
            filters={
                "id": f"eq.{job_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def insert(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.insert("study_sheet_jobs", payload)
        return rows[0]

    async def update(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.update(
            "study_sheet_jobs",
            filters={"id": f"eq.{job_id}"},
            payload=payload,
        )
        return rows[0]
