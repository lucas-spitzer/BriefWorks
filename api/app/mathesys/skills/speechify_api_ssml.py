from __future__ import annotations

from typing import Any

from app.mathesys.skills.narration_base import NarrationSkillBase, emit_ssml_volume


class SpeechifyApiSsmlSkill(NarrationSkillBase):
    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
        audience: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return self.run_volumes(
            source_metadata=source_metadata,
            segments=segments,
            wiki_entries=wiki_entries,
            audience=audience,
            emit_volume=emit_ssml_volume(),
            transformations=[
                "audio_document_normalization",
                "speechify_ssml_emission",
                "section_pause_tags",
            ],
        )
