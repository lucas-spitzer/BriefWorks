from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NarrationSegmentResponse(BaseModel):
    id: str
    source_id: str
    workspace_id: str
    chapter_id: str | None = None
    segment_id: str
    voice_id: str
    model_id: str
    duration_seconds: float
    # Word timings [{i, w, s, e}] — word index, word, start/end seconds.
    words: list[dict[str, Any]]
    created_at: datetime


class NarrationAudioResponse(BaseModel):
    segment_id: str
    audio_url: str
    expires_in: int
