from __future__ import annotations

from typing import Any

from app.mathesys.study_sheet.generate import StudySheetResult
from app.worker.study_sheet_job import run_study_sheet_job


class FakeDb:
    def __init__(self, job: dict[str, Any]) -> None:
        self.job = job
        self.created_artifacts: list[dict[str, Any]] = []
        self.updates: list[dict[str, Any]] = []

    def get_study_sheet_job(self, job_id: str) -> dict[str, Any] | None:
        if self.job.get("id") != job_id:
            return None
        return self.job

    def update_study_sheet_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        del job_id
        self.updates.append(payload)
        self.job = {**self.job, **payload}
        return self.job

    def get_sources(self, source_ids: list[str]) -> list[dict[str, Any]]:
        del source_ids
        return [
            {
                "id": "src-1",
                "slug": "ocs",
                "workspace_slug": "ocs-prep",
                "workspace_id": "ws-1",
            }
        ]

    def list_artifacts_for_source(
        self,
        source_id: str,
        *,
        artifact_type: str | None = None,
    ) -> list[dict[str, Any]]:
        del source_id, artifact_type
        return []

    def update_artifact(self, artifact_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        del artifact_id
        self.created_artifacts.append(payload)
        return {**payload, "id": "art-1"}

    def create_artifact(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.created_artifacts.append(payload)
        return {**payload, "id": payload.get("id") or "art-1"}


class FakeStorage:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.uploads: list[tuple[str, bytes]] = []

    def download(self, path: str, *, bucket: str | None = None) -> bytes:
        del path, bucket
        return self.content

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


def test_run_study_sheet_job_writes_workspace_pdf(monkeypatch: Any) -> None:
    from app.worker import study_sheet_job as module

    job = {
        "id": "job-1",
        "workspace_id": "ws-1",
        "source_id": "src-1",
        "status": "queued",
        "input_filename": "ocs.md",
        "input_mime_type": "text/markdown",
        "input_storage_path": "ocs-prep/ocs/ocs.md",
    }
    db = FakeDb(job)
    storage = FakeStorage(b"## Orders\n\n1. Take charge.")

    monkeypatch.setattr(module, "WorkerDatabase", lambda: db)
    monkeypatch.setattr(module, "WorkerStorage", lambda: storage)
    monkeypatch.setattr(module, "get_settings", lambda: type("S", (), {"study_sheet": type("T", (), {"max_attempts": 3})()})())
    monkeypatch.setattr(module, "get_llm_client", lambda action: object())
    monkeypatch.setattr(module, "WeasyPrintPdfPrinter", lambda: object())
    monkeypatch.setattr(
        module,
        "generate_study_sheet",
        lambda **kwargs: StudySheetResult(
            title="OCS Knowledge Review",
            html="<html>sheet</html>",
            pdf=b"%PDF-fake",
            page_count=2,
            attempt_count=1,
            model="gemini-3.7-flash",
            provider="google",
            token_usages=[{"input_tokens": 8, "output_tokens": 4, "total_tokens": 12}],
        ),
    )
    monkeypatch.setattr(
        module,
        "cost_llm_usage",
        lambda **kwargs: {"cost_usd": 0.001},
    )

    result = run_study_sheet_job("job-1")

    assert result["status"] == "completed"
    assert result["page_count"] == 2
    assert db.created_artifacts[0]["artifact_type"] == "study_sheet"
    assert db.created_artifacts[0]["source_id"] == "src-1"
    assert db.created_artifacts[0]["storage_path"] == "ocs-prep/ocs/sheet.pdf"
    assert db.created_artifacts[0]["filename"] == "sheet.pdf"
    assert any(path.endswith(".pdf") for path, _ in storage.uploads)
    assert not any(path.endswith(".html") for path, _ in storage.uploads)


def test_run_study_sheet_job_skips_non_queued(monkeypatch: Any) -> None:
    from app.worker import study_sheet_job as module

    db = FakeDb({"id": "job-1", "status": "completed"})
    monkeypatch.setattr(module, "WorkerDatabase", lambda: db)
    monkeypatch.setattr(module, "WorkerStorage", lambda: FakeStorage(b""))
    monkeypatch.setattr(module, "get_settings", lambda: type("S", (), {"study_sheet": type("T", (), {"max_attempts": 3})()})())

    result = run_study_sheet_job("job-1")
    assert result["skipped"] is True
