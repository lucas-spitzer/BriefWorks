from __future__ import annotations

from typing import Any

from app.mathesys.audio.models import AudioDocument, PronunciationEntry
from app.mathesys.audio.segment_text import infer_source_type
from app.mathesys.audio.segment_to_document import (
    build_glossary_from_wiki,
    chapter_text_blob,
    chapter_to_audio_section,
)


class AudioDocumentBuilder:
    """Build AudioDocument structures from prepared NDR segments.

    Body and heading text are passed through verbatim. Upstream Intellex
    prepare/chunk steps own all content removal; this builder
    only recovers hierarchy for TTS emitters.
    """

    def build_document(
        self,
        *,
        title: str,
        author: str | None,
        source_metadata: dict[str, Any],
        chapters: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
        language: str = "en-US",
        audience: str | None = None,
    ) -> tuple[AudioDocument, dict[str, Any]]:
        sections = []
        glossary: list[PronunciationEntry] = []
        segment_ids: set[str] = set()
        wiki_ids: set[str] = set()

        for chapter in chapters:
            build_result = chapter_to_audio_section(chapter)
            sections.append(build_result.section)
            segment_ids.update(build_result.segment_ids_used)

            chapter_glossary, chapter_wiki_ids = build_glossary_from_wiki(
                wiki_entries,
                chapter_text=chapter_text_blob(chapter),
            )
            glossary.extend(chapter_glossary)
            wiki_ids.update(chapter_wiki_ids)

        document = AudioDocument(
            title=title,
            author=author,
            language=language,
            source_type=infer_source_type(source_metadata),  # type: ignore[arg-type]
            audience=audience,
            sections=sections,
            glossary=glossary,
        )

        return document, {
            "model": "deterministic-passthrough",
            "token_usage": {},
            "segment_ids_used": sorted(segment_ids),
            "wiki_ids_cited": sorted(wiki_ids),
        }
