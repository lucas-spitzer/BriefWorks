from __future__ import annotations

from typing import Any

from app.intellex.stages.models import SourceResearchOutput


def merge_research_into_source_metadata(
    existing_metadata: dict[str, Any] | None,
    research: SourceResearchOutput,
    *,
    researched_at: str,
) -> dict[str, Any]:
    metadata = dict(existing_metadata or {})
    metadata["research"] = research.to_metadata(researched_at=researched_at)
    return metadata
