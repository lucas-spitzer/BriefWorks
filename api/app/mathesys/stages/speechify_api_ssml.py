from __future__ import annotations

from typing import Any

from app.mathesys.stages.narration_base import NarrationStageBase, emit_ssml_volume


class SpeechifyApiSsmlStage(NarrationStageBase):
    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
        chapter_rows: list[dict[str, Any]] | None = None,
        audience: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return self.run_volumes(
            source_metadata=source_metadata,
            segments=segments,
            wiki_entries=wiki_entries,
            chapter_rows=chapter_rows,
            audience=audience,
            emit_volume=emit_ssml_volume(),
            transformations=[
                "prepared_segment_passthrough",
                "speechify_ssml_emission",
                "section_pause_tags",
            ],
        )
