from __future__ import annotations

from typing import Any

from app.mathesys.audio.models import ElevenLabsMode
from app.mathesys.stages.narration_base import NarrationStageBase, emit_eleven_labs_volume


class ElevenLabsStructuredTextStage(NarrationStageBase):
    def __init__(
        self,
        *,
        mode: ElevenLabsMode = "expressive_v3",
        model_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.mode = mode
        self.model_id = model_id

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
            emit_volume=emit_eleven_labs_volume(mode=self.mode, model_id=self.model_id),
            transformations=[
                "prepared_segment_passthrough",
                "elevenlabs_structured_text",
                "section_pause_approximation" if self.mode == "expressive_v3" else "section_pause_breaks",
            ],
        )
