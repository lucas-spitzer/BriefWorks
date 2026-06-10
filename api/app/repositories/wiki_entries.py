from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class WikiEntryRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_for_workspace(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        search: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        filters: dict[str, str] = {"workspace_id": f"eq.{workspace_id}"}

        if status:
            filters["status"] = f"eq.{status}"

        if search:
            filters["or"] = (
                f"(preferred_label.ilike.*{search}*,definition.ilike.*{search}*)"
            )

        return await self.db.select_many(
            "wiki_entries",
            filters=filters,
            order="preferred_label.asc",
            limit=limit,
            offset=offset,
        )

    async def get_for_workspace(
        self,
        wiki_entry_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "wiki_entries",
            filters={
                "id": f"eq.{wiki_entry_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def list_disputes_for_workspace(
        self,
        workspace_id: str,
        *,
        status: str | None = "open",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        filters: dict[str, str] = {"workspace_id": f"eq.{workspace_id}"}

        if status:
            filters["status"] = f"eq.{status}"

        return await self.db.select_many(
            "wiki_disputes",
            filters=filters,
            order="created_at.desc",
            limit=limit,
        )
