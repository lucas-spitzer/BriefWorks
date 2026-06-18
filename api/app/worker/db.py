import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[2]
load_dotenv(API_DIR / ".env")

NDR_SEGMENT_BATCH_SIZE = 200


class WorkerDatabase:
    def __init__(self) -> None:
        supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
        service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.base_url = f"{supabase_url}/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, str] | None = None,
        json_body: Any | None = None,
    ) -> Any:
        with httpx.Client(timeout=60) as client:
            response = client.request(
                method,
                f"{self.base_url}/{table}",
                headers=self.headers,
                params=params,
                json=json_body,
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"Supabase REST request failed ({response.status_code}): {detail}",
            )

        if response.status_code == 204 or not response.content:
            return None

        return response.json()

    def get_production_run(self, production_run_id: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "production_runs",
            params={
                "select": "*",
                "id": f"eq.{production_run_id}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def update_production_run(
        self,
        production_run_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            "production_runs",
            params={"id": f"eq.{production_run_id}"},
            json_body=payload,
        )
        return rows[0]

    def get_sources(self, source_ids: list[str]) -> list[dict[str, Any]]:
        if not source_ids:
            return []

        formatted_ids = ",".join(source_ids)
        rows = self._request(
            "GET",
            "sources",
            params={
                "select": "*",
                "id": f"in.({formatted_ids})",
            },
        )
        return rows or []

    def update_source(self, source_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            "sources",
            params={"id": f"eq.{source_id}"},
            json_body=payload,
        )
        return rows[0]

    def delete_ndr_segments_for_source(self, source_id: str) -> None:
        self._request(
            "DELETE",
            "ndr_segments",
            params={"source_id": f"eq.{source_id}"},
        )

    def delete_document_chapters_for_source(self, source_id: str) -> None:
        self._request(
            "DELETE",
            "document_chapters",
            params={"source_id": f"eq.{source_id}"},
        )

    def insert_document_chapters(self, chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not chapters:
            return []

        created: list[dict[str, Any]] = []

        for start in range(0, len(chapters), NDR_SEGMENT_BATCH_SIZE):
            batch = chapters[start : start + NDR_SEGMENT_BATCH_SIZE]
            created.extend(self._request("POST", "document_chapters", json_body=batch) or [])

        return created

    def list_document_chapters_for_source(self, source_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "document_chapters",
            params={
                "select": "*",
                "source_id": f"eq.{source_id}",
                "order": "sequence_index.asc",
            },
        )
        return rows or []

    def has_document_chapters_for_source(self, source_id: str) -> bool:
        rows = self._request(
            "GET",
            "document_chapters",
            params={
                "select": "id",
                "source_id": f"eq.{source_id}",
                "limit": "1",
            },
        )
        return bool(rows)

    def insert_ndr_segments(self, segments: list[dict[str, Any]]) -> None:
        if not segments:
            return

        for start in range(0, len(segments), NDR_SEGMENT_BATCH_SIZE):
            batch = segments[start : start + NDR_SEGMENT_BATCH_SIZE]
            self._request("POST", "ndr_segments", json_body=batch)

    def create_skill_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request("POST", "skill_runs", json_body=payload)
        return rows[0]

    def update_skill_run(self, skill_run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            "skill_runs",
            params={"id": f"eq.{skill_run_id}"},
            json_body=payload,
        )
        return rows[0]

    def get_skill(self, skill_id: str, version: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "skills",
            params={
                "select": "*",
                "skill_id": f"eq.{skill_id}",
                "version": f"eq.{version}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def list_ndr_segments_for_source(self, source_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "ndr_segments",
            params={
                "select": "*",
                "source_id": f"eq.{source_id}",
                "order": "sequence_index.asc",
            },
        )
        return rows or []

    def has_completed_skill_run_for_source(self, source_id: str, skill_id: str) -> bool:
        rows = self._request(
            "GET",
            "skill_runs",
            params={
                "select": "id",
                "skill_id": f"eq.{skill_id}",
                "status": "eq.completed",
                "inputs->>source_id": f"eq.{source_id}",
                "limit": "1",
            },
        )
        return bool(rows)

    def list_wiki_entries_for_workspace(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "wiki_entries",
            params={
                "select": "*",
                "workspace_id": f"eq.{workspace_id}",
                "order": "preferred_label.asc",
            },
        )
        return rows or []

    def insert_wiki_entries(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        created: list[dict[str, Any]] = []

        for start in range(0, len(rows), NDR_SEGMENT_BATCH_SIZE):
            batch = rows[start : start + NDR_SEGMENT_BATCH_SIZE]
            created.extend(self._request("POST", "wiki_entries", json_body=batch) or [])

        return created

    def update_wiki_entry(self, wiki_entry_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            "wiki_entries",
            params={"id": f"eq.{wiki_entry_id}"},
            json_body=payload,
        )
        return rows[0]

    def insert_wiki_disputes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        return self._request("POST", "wiki_disputes", json_body=rows) or []

    def create_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request("POST", "artifacts", json_body=payload)
        return rows[0]

    def update_artifact(self, artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            "artifacts",
            params={"id": f"eq.{artifact_id}"},
            json_body=payload,
        )
        return rows[0]

    def list_artifacts_for_workspace(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "artifacts",
            params={
                "select": "*",
                "workspace_id": f"eq.{workspace_id}",
                "order": "created_at.desc",
            },
        )
        return rows or []

    def get_artifact(self, artifact_id: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "artifacts",
            params={
                "select": "*",
                "id": f"eq.{artifact_id}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    def insert_flashcards(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        created: list[dict[str, Any]] = []

        for start in range(0, len(rows), NDR_SEGMENT_BATCH_SIZE):
            batch = rows[start : start + NDR_SEGMENT_BATCH_SIZE]
            created.extend(self._request("POST", "flashcards", json_body=batch) or [])

        return created

    def insert_quizzes(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        created: list[dict[str, Any]] = []

        for start in range(0, len(rows), NDR_SEGMENT_BATCH_SIZE):
            batch = rows[start : start + NDR_SEGMENT_BATCH_SIZE]
            created.extend(self._request("POST", "quizzes", json_body=batch) or [])

        return created

    def sum_skill_run_costs(self, production_run_id: str) -> float:
        rows = self._request(
            "GET",
            "skill_runs",
            params={
                "select": "cost_usd",
                "production_run_id": f"eq.{production_run_id}",
            },
        )

        return round(
            sum(float(row.get("cost_usd") or 0) for row in (rows or [])),
            6,
        )

    def list_skill_runs_for_production_run(
        self,
        production_run_id: str,
    ) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "skill_runs",
            params={
                "select": "*",
                "production_run_id": f"eq.{production_run_id}",
                "order": "created_at.asc",
            },
        )
        return rows or []

    def list_skill_runs_for_workspace(
        self,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "skill_runs",
            params={
                "select": "*",
                "workspace_id": f"eq.{workspace_id}",
                "order": "created_at.asc",
            },
        )
        return rows or []

    def insert_scenarios(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        created: list[dict[str, Any]] = []

        for start in range(0, len(rows), NDR_SEGMENT_BATCH_SIZE):
            batch = rows[start : start + NDR_SEGMENT_BATCH_SIZE]
            created.extend(self._request("POST", "scenarios", json_body=batch) or [])

        return created

    def insert_assessment_set(self, row: dict[str, Any]) -> dict[str, Any]:
        created = self._request("POST", "assessment_sets", json_body=row)
        if isinstance(created, list):
            return created[0]
        return created
