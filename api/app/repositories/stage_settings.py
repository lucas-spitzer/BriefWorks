from typing import Any

from app.services.supabase_rest import SupabaseRestClient

TABLE = "workspace_stage_settings"


class StageSettingsRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_for_workspace(self, workspace_id: str) -> list[dict[str, Any]]:
        return await self.db.select_many(
            TABLE,
            filters={"workspace_id": f"eq.{workspace_id}"},
        )

    async def upsert(
        self,
        *,
        workspace_id: str,
        stage_action: str,
        provider: str,
        model: str,
        reasoning_effort: str | None,
        reasoning_tokens: int | None,
    ) -> dict[str, Any]:
        rows = await self.db.request(
            "POST",
            TABLE,
            params={"on_conflict": "workspace_id,stage_action"},
            json_body={
                "workspace_id": workspace_id,
                "stage_action": stage_action,
                "provider": provider,
                "model": model,
                "reasoning_effort": reasoning_effort,
                "reasoning_tokens": reasoning_tokens,
            },
            prefer="return=representation,resolution=merge-duplicates",
        )
        return rows[0]

    async def delete(self, *, workspace_id: str, stage_action: str) -> None:
        await self.db.delete(
            TABLE,
            filters={
                "workspace_id": f"eq.{workspace_id}",
                "stage_action": f"eq.{stage_action}",
            },
        )
