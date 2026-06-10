from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SkillRunResponse(BaseModel):
    id: str
    production_run_id: str | None
    workspace_id: str
    skill_id: str
    skill_version: str
    module: str
    status: str
    inputs: dict[str, Any]
    output: dict[str, Any] | None
    promoted: dict[str, Any]
    model: str | None
    token_usage: dict[str, Any]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
