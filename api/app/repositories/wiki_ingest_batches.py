from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class WikiIngestBatchRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_for_workspace(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        filters: dict[str, str] = {"workspace_id": f"eq.{workspace_id}"}

        if status:
            filters["status"] = f"eq.{status}"

        return await self.db.select_many(
            "wiki_ingest_batches",
            filters=filters,
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

    async def get_for_workspace(
        self,
        batch_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "wiki_ingest_batches",
            filters={
                "id": f"eq.{batch_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def insert(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.insert("wiki_ingest_batches", payload)
        return rows[0]

    async def update(self, batch_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = await self.db.update(
            "wiki_ingest_batches",
            filters={"id": f"eq.{batch_id}"},
            payload=payload,
        )
        return rows[0]

    async def list_chapters_for_source(self, source_id: str) -> list[dict[str, Any]]:
        """Chapter rows for chapter-hint resolution and evidence scoping.

        Workspace access is already enforced by the router (require_workspace +
        source ownership), so this stays a plain source-scoped read.
        """
        return await self.db.select_many(
            "document_chapters",
            filters={"source_id": f"eq.{source_id}"},
            order="sequence_index.asc",
            limit=500,
        )
