from typing import Literal

from pydantic import BaseModel, Field


class ReaderDefineRequest(BaseModel):
    term: str = Field(min_length=1, max_length=200)
    mode: Literal["contextual", "general"]
    source_id: str | None = None
    sentence: str | None = None
    prev_paragraph: str | None = None
    current_paragraph: str | None = None
    next_paragraph: str | None = None


class ReaderDefineResponse(BaseModel):
    term: str
    definition: str
    mode: Literal["contextual", "general"]
    provenance: Literal["contextual", "general"]
