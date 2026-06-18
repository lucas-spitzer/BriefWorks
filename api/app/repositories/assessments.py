from typing import Any

from app.services.supabase_rest import SupabaseRestClient


class AssessmentRepository:
    def __init__(self, db: SupabaseRestClient) -> None:
        self.db = db

    async def list_flashcards(
        self,
        workspace_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "flashcards",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

    async def get_flashcard(
        self,
        flashcard_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "flashcards",
            filters={
                "id": f"eq.{flashcard_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def list_quizzes(
        self,
        workspace_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "quizzes",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

    async def get_quiz(
        self,
        quiz_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "quizzes",
            filters={
                "id": f"eq.{quiz_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def list_scenarios(
        self,
        workspace_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await self.db.select_many(
            "scenarios",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

    async def get_scenario(
        self,
        scenario_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "scenarios",
            filters={
                "id": f"eq.{scenario_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def get_flashcard_for_owner(
        self,
        flashcard_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        row = await self.db.select_one("flashcards", filters={"id": f"eq.{flashcard_id}"})
        if not row:
            return None
        return await self._verify_workspace_owner(row["workspace_id"], owner_id, row)

    async def get_quiz_for_owner(
        self,
        quiz_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        row = await self.db.select_one("quizzes", filters={"id": f"eq.{quiz_id}"})
        if not row:
            return None
        return await self._verify_workspace_owner(row["workspace_id"], owner_id, row)

    async def get_scenario_for_owner(
        self,
        scenario_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        row = await self.db.select_one("scenarios", filters={"id": f"eq.{scenario_id}"})
        if not row:
            return None
        return await self._verify_workspace_owner(row["workspace_id"], owner_id, row)

    async def _verify_workspace_owner(
        self,
        workspace_id: str,
        owner_id: str,
        row: dict[str, Any],
    ) -> dict[str, Any] | None:
        workspace = await self.db.select_one(
            "workspaces",
            filters={
                "id": f"eq.{workspace_id}",
                "owner_id": f"eq.{owner_id}",
            },
            columns="id",
        )
        return row if workspace else None

    async def list_assessment_sets(
        self,
        workspace_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        rows = await self.db.select_many(
            "assessment_sets",
            filters={"workspace_id": f"eq.{workspace_id}"},
            order="created_at.desc",
            limit=limit,
            offset=offset,
        )

        summaries: list[dict[str, Any]] = []
        for row in rows:
            items = row.get("items") or []
            summaries.append(
                {
                    **row,
                    "item_count": len(items) if isinstance(items, list) else 0,
                },
            )
        return summaries

    async def get_assessment_set(
        self,
        assessment_set_id: str,
        workspace_id: str,
    ) -> dict[str, Any] | None:
        return await self.db.select_one(
            "assessment_sets",
            filters={
                "id": f"eq.{assessment_set_id}",
                "workspace_id": f"eq.{workspace_id}",
            },
        )

    async def get_assessment_set_for_owner(
        self,
        assessment_set_id: str,
        owner_id: str,
    ) -> dict[str, Any] | None:
        row = await self.db.select_one(
            "assessment_sets",
            filters={"id": f"eq.{assessment_set_id}"},
        )
        if not row:
            return None
        return await self._verify_workspace_owner(row["workspace_id"], owner_id, row)
