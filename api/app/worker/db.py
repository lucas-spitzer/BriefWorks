import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from app.services.embeddings import EmbeddingClient, get_embedding_client, to_pgvector_literal

API_DIR = Path(__file__).resolve().parents[2]
load_dotenv(API_DIR / ".env")

logger = logging.getLogger(__name__)

NDR_SEGMENT_BATCH_SIZE = 200


# Wiki writes moved to the API's wiki-authoring flow (services/wiki_authoring.py);
# the worker only reads wiki_entries now.


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
        self._embedding_client: EmbeddingClient | None = None

    @property
    def embedding_client(self) -> EmbeddingClient:
        if self._embedding_client is None:
            self._embedding_client = get_embedding_client()
        return self._embedding_client

    def _stamp_embeddings(self, rows: list[dict[str, Any]], texts: list[str]) -> None:
        """Best-effort: embed `texts` and stamp embedding + embedded_at onto rows.

        Failures (missing key, API error) are logged and swallowed — the rows
        still persist with a null embedding, and scripts.backfill_embeddings can
        fill the gap later.
        """
        if not rows:
            return
        try:
            vectors = self.embedding_client.embed(texts)
        except Exception:  # noqa: BLE001 - embedding is non-critical to ingest
            logger.warning("Embed-on-write failed; rows persisted unembedded.", exc_info=True)
            return

        now = datetime.now(timezone.utc).isoformat()
        for row, vector in zip(rows, vectors):
            row["embedding"] = to_pgvector_literal(vector)
            row["embedded_at"] = now

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

    def list_sources_for_workspace(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "sources",
            params={
                "select": "*",
                "workspace_id": f"eq.{workspace_id}",
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
            self._stamp_embeddings(batch, [row.get("text", "") or " " for row in batch])
            self._request("POST", "ndr_segments", json_body=batch)

    def list_narration_segments_for_source(
        self, source_id: str, voice_id: str
    ) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "narration_segments",
            params={
                "select": "*",
                "source_id": f"eq.{source_id}",
                "voice_id": f"eq.{voice_id}",
                "order": "created_at.asc",
            },
        )
        return rows or []

    def list_narrated_segment_ids_for_source(
        self, source_id: str, voice_id: str
    ) -> set[str]:
        rows = self._request(
            "GET",
            "narration_segments",
            params={
                "select": "segment_id",
                "source_id": f"eq.{source_id}",
                "voice_id": f"eq.{voice_id}",
            },
        )
        return {row["segment_id"] for row in rows or []}

    def insert_narration_segment(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request("POST", "narration_segments", json_body=payload)
        return rows[0] if isinstance(rows, list) and rows else {}

    def list_workspace_stage_settings(self, workspace_id: str) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "workspace_stage_settings",
            params={
                "select": "*",
                "workspace_id": f"eq.{workspace_id}",
            },
        )
        return rows or []

    def create_stage_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request("POST", "stage_runs", json_body=payload)
        return rows[0]

    def update_stage_run(self, stage_run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self._request(
            "PATCH",
            "stage_runs",
            params={"id": f"eq.{stage_run_id}"},
            json_body=payload,
        )
        return rows[0]

    def get_stage(self, stage_id: str, version: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "stages",
            params={
                "select": "*",
                "stage_id": f"eq.{stage_id}",
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

    def has_completed_stage_run_for_source(self, source_id: str, stage_id: str) -> bool:
        rows = self._request(
            "GET",
            "stage_runs",
            params={
                "select": "id",
                "stage_id": f"eq.{stage_id}",
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

    def sum_stage_run_costs(self, production_run_id: str) -> float:
        rows = self._request(
            "GET",
            "stage_runs",
            params={
                "select": "cost_usd",
                "production_run_id": f"eq.{production_run_id}",
            },
        )

        return round(
            sum(float(row.get("cost_usd") or 0) for row in (rows or [])),
            6,
        )

    def list_stage_runs_for_production_run(
        self,
        production_run_id: str,
    ) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "stage_runs",
            params={
                "select": "*",
                "production_run_id": f"eq.{production_run_id}",
                "order": "created_at.asc",
            },
        )
        return rows or []

    def list_stage_runs_for_workspace(
        self,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            "stage_runs",
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
