from datetime import datetime
from typing import Any

from pydantic import BaseModel


class StageResponse(BaseModel):
    id: str
    stage_id: str
    version: str
    module: str
    name: str
    description: str | None
    modalities: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    prompts: dict[str, Any]
    is_active: bool
    created_at: datetime
