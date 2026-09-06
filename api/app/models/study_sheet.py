from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

StudySheetJobStatus = Literal["queued", "running", "completed", "failed"]


class StudySheetJobResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str | None = None
    status: StudySheetJobStatus
    input_filename: str
    input_mime_type: str
    input_storage_path: str
    input_file_size_bytes: int
    artifact_id: str | None
    attempt_count: int
    page_count: int | None
    error: str | None
    model: str | None
    cost_usd: float | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


def job_row_to_response(row: dict[str, Any]) -> StudySheetJobResponse:
    return StudySheetJobResponse.model_validate(row)
