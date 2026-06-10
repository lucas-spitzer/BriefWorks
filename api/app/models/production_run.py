from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProductionRunCreate(BaseModel):
    source_ids: list[str] = Field(min_length=1)
    target_artifacts: list[str] = Field(default_factory=list)


class ProductionRunResponse(BaseModel):
    id: str
    workspace_id: str
    owner_id: str
    source_ids: list[str]
    target_artifacts: list[str]
    pipeline: list[dict[str, Any]]
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
