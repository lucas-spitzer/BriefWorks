from __future__ import annotations

from typing import Any

from app.mathesys.study_sheet.generate import StudySheetResult
from app.worker.study_sheet_executor import CreateStudySheetStageExecutor


class FakeDb:
    def __init__(self) -> None:
        self.stage_runs: list[dict[str, Any]] = []
        self.created_artifacts: list[dict[str, Any]] = []
        self.updated_runs: list[dict[str, Any]] = []

    def create_stage_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**payload, "id": "stage-1"}
        self.stage_runs.append(row)
        return row

    def update_stage_run(self, stage_run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        del stage_run_id
        self.updated_runs.append(payload)
        return payload

    def list_artifacts_for_source(
        self,
        source_id: str,
        *,
        artifact_type: str | None = None,
    ) -> list[dict[str, Any]]:
        del source_id, artifact_type
        return []

    def create_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = {**payload, "id": "art-1"}
        self.created_artifacts.append(row)
        return row

    def update_artifact(self, artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        del artifact_id
        row = {**payload, "id": "art-1"}
        self.created_artifacts.append(row)
        return row


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes]] = []

    def download(self, path: str, *, bucket: str | None = None) -> bytes:
        del path, bucket
        return b"%PDF-source"

    def upload(
        self,
        path: str,
        content: bytes,
        *,
        bucket: str | None = None,
        content_type: str = "application/octet-stream",
        upsert: bool = True,
    ) -> None:
        del bucket, content_type, upsert
        self.uploads.append((path, content))


def test_study_sheet_stage_writes_sheet_pdf(monkeypatch: Any) -> None:
    from app.worker import study_sheet_executor as module

    db = FakeDb()
    storage = FakeStorage()
    monkeypatch.setattr(
        module,
        "get_settings",
        lambda: type("S", (), {"study_sheet": type("T", (), {"max_attempts": 3})()})(),
    )
    monkeypatch.setattr(module, "get_llm_client", lambda action: object())
    monkeypatch.setattr(module, "WeasyPrintPdfPrinter", lambda: object())
    monkeypatch.setattr(
        module,
        "generate_study_sheet",
        lambda **kwargs: StudySheetResult(
            title="Warfighting",
            html="<html>sheet</html>",
            pdf=b"%PDF-sheet",
            page_count=2,
            attempt_count=1,
            model="gemini-3.7-flash",
            provider="google",
            token_usages=[{"input_tokens": 10, "output_tokens": 4, "total_tokens": 14}],
        ),
    )

    executor = CreateStudySheetStageExecutor(db=db, storage=storage)
    stage_run_id = executor.run_for_source(
        production_run_id="run-1",
        workspace_id="ws-1",
        source={
            "id": "src-1",
            "slug": "mcdp-1-warfighting",
            "workspace_slug": "marine-corps-doctrine",
            "filename": "MCDP 1 Warfighting.pdf",
            "mime_type": "application/pdf",
            "storage_path": "marine-corps-doctrine/mcdp-1-warfighting/MCDP 1 Warfighting.pdf",
        },
    )

    assert stage_run_id == "stage-1"
    assert db.created_artifacts[0]["artifact_type"] == "study_sheet"
    assert db.created_artifacts[0]["production_run_id"] == "run-1"
    assert db.created_artifacts[0]["storage_path"] == (
        "marine-corps-doctrine/mcdp-1-warfighting/sheet.pdf"
    )
    assert storage.uploads == [("marine-corps-doctrine/mcdp-1-warfighting/sheet.pdf", b"%PDF-sheet")]
    assert db.updated_runs[0]["status"] == "completed"
    assert db.updated_runs[0]["cost_usd"] is not None
