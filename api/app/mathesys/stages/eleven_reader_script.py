from __future__ import annotations

from typing import Any

from app.mathesys.stages.elevenreader_epub import build_single_elevenreader_epub
from app.mathesys.stages.narration_base import NarrationStageBase


class ElevenReaderScriptStage(NarrationStageBase):
    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
        chapter_rows: list[dict[str, Any]] | None = None,
        audience: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return build_single_elevenreader_epub(
            source_metadata=source_metadata,
            segments=segments,
            chapter_rows=chapter_rows,
            wiki_entries=wiki_entries,
            audience=audience,
            narration_base=self,
        )
