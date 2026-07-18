from datetime import datetime

from pydantic import BaseModel, Field


class DocumentChapterSection(BaseModel):
    title: str
    level: int
    sequence_index: int
    heading_segment_id: str
    segment_ids: list[str]


class DocumentChapterResponse(BaseModel):
    id: str
    source_id: str
    workspace_id: str
    sequence_index: int
    title: str
    level: int
    segment_ids: list[str]
    sections: list[DocumentChapterSection] = Field(default_factory=list)
    created_at: datetime
