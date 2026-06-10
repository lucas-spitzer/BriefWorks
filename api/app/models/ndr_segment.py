from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NdrSegmentResponse(BaseModel):
    id: str
    source_id: str
    workspace_id: str
    sequence_index: int
    kind: str
    text: str
    locator: dict[str, Any]
    created_at: datetime
