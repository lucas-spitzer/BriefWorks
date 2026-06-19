from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WikiEntryResponse(BaseModel):
    id: str
    workspace_id: str
    preferred_label: str
    canonical_slug: str
    definition: str
    pronunciation: str | None
    aliases: list[str]
    prerequisites: list[str]
    importance: str
    entry_kind: str
    status: str
    evidence: list[dict[str, Any]]
    origin: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WikiDisputeResponse(BaseModel):
    id: str
    workspace_id: str
    wiki_entry_id: str | None
    term_label: str
    existing_definition: str | None
    proposed_definition: str
    stage_run_id: str | None
    source_id: str | None
    status: str
    created_at: datetime
