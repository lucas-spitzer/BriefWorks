from __future__ import annotations

from pydantic import BaseModel, Field


class TransformedSection(BaseModel):
    heading: str | None = None
    heading_level: int = 2
    paragraphs: list[str] = Field(default_factory=list)


class TransformedChapter(BaseModel):
    title: str
    sections: list[TransformedSection] = Field(default_factory=list)
    wiki_ids_cited: list[str] = Field(default_factory=list)
    segment_ids_used: list[str] = Field(default_factory=list)


class ElevenReaderScriptOutput(BaseModel):
    chapters: list[TransformedChapter]
