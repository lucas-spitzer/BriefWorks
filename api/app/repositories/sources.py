from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class SourceRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.insert("sources", payload)
        return rows[0]

    async def list_slugs_for_workspace(self, workspace_id: str) -> set[str]:
        rows = await self.db.select_many(
            "sources",
            filters={"workspace_id": f"eq.{workspace_id}"},
            columns="slug",
        )
        return {str(row["slug"]) for row in rows if row.get("slug")}

    async def get_by_hash(
        self,
        workspace_id: str,
        file_hash: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "sources",
            filters={
                "workspace_id": f"eq.{workspace_id}",
                "file_hash": f"eq.{file_hash}",
            },
        )

    async def list_for_workspace(
        self,
        workspace_id: str,
        owner_id: str,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "sources",
            filters={
                "workspace_id": f"eq.{workspace_id}",
                "owner_id": f"eq.{owner_id}",
            },
            order="created_at.desc",
        )

    async def get_for_workspace(
        self,
        source_id: str,
        workspace_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "sources",
            filters={
                "id": f"eq.{source_id}",
                "workspace_id": f"eq.{workspace_id}",
                "owner_id": f"eq.{owner_id}",
            },
        )

    async def get_many_for_workspace(
        self,
        source_ids: list[str],
        workspace_id: str,
        owner_id: str,
    ) -> list[dict[str, Any]]:
        if not source_ids:
            return []

        formatted_ids = ",".join(source_ids)
        return await self.db.select_many(
            "sources",
            filters={
                "id": f"in.({formatted_ids})",
                "workspace_id": f"eq.{workspace_id}",
                "owner_id": f"eq.{owner_id}",
            },
        )

    async def delete(
        self,
        source_id: str,
        workspace_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        source = await self.get_for_workspace(source_id, workspace_id, owner_id)

        if not source:
            return None

        await self.db.delete(
            "sources",
            filters={
                "id": f"eq.{source_id}",
                "workspace_id": f"eq.{workspace_id}",
                "owner_id": f"eq.{owner_id}",
            },
        )
        return source
