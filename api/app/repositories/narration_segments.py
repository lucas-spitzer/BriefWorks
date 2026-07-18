from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class NarrationSegmentRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_for_source(
        self,
        source_id: str,
        workspace_id: str,
        owner_id: str,
        *,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        await self._assert_source_access(source_id, workspace_id, owner_id)

        return await self.db.select_many(
            "narration_segments",
            filters={
                "source_id": f"eq.{source_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
            order="created_at.asc",
            limit=limit,
            offset=offset,
        )

    async def get_for_segment(
        self,
        source_id: str,
        segment_id: str,
        workspace_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        await self._assert_source_access(source_id, workspace_id, owner_id)

        return await self.db.select_one(
            "narration_segments",
            filters={
                "source_id": f"eq.{source_id}",
                "segment_id": f"eq.{segment_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def _assert_source_access(
        self,
        source_id: str,
        workspace_id: str,
        owner_id: str,
    ) -> None:
        source = await self.db.select_one(
            "sources",
            filters={
                "id": f"eq.{source_id}",
                "workspace_id": f"eq.{workspace_id}",
                "owner_id": f"eq.{owner_id}",
            },
            columns="id",
        )

        if not source:
            raise LookupError("Source not found.")
