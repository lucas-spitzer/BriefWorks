from __future__ import annotations

import uuid
from typing import Any

from app.mathesys.audio.models import (
    AudioParagraph,
    AudioSection,
    ChapterBuildResult,
    PronunciationEntry,
)


def _segment_text(segment: dict[str, Any]) -> str:
    """Return segment text exactly as stored — only strip outer whitespace."""
    return str(segment.get("text") or "").strip()


def chapter_to_audio_section(chapter: dict[str, Any]) -> ChapterBuildResult:
    """Map prepared NDR chapter segments to AudioSection without altering text."""
    segments = chapter.get("segments") or []
    chapter_title = _segment_text({"text": chapter.get("title")}) or "Untitled Section"

    if not segments:
        return ChapterBuildResult(
            section=AudioSection(
                id=f"section-{uuid.uuid4()}",
                level=1,
                title=chapter_title,
            ),
            segment_ids_used=[],
            wiki_ids_cited=[],
        )

    section_id = f"section-{segments[0].get('id') or uuid.uuid4()}"
    segment_ids_used: list[str] = []
    paragraphs: list[AudioParagraph] = []
    subsections: list[AudioSection] = []
    current_subsection: AudioSection | None = None

    for index, segment in enumerate(segments):
        segment_id = str(segment.get("id") or f"segment-{index}")
        segment_ids_used.append(segment_id)

        text = _segment_text(segment)
        if not text:
            continue

        kind = str(segment.get("kind") or "paragraph")

        if kind == "heading":
            # The chapter title already comes from the first heading when present.
            if index == 0 and text == chapter_title:
                continue

            if current_subsection is not None:
                subsections.append(current_subsection)

            current_subsection = AudioSection(
                id=f"subsection-{segment_id}",
                level=2,
                title=text,
            )
            continue

        paragraph = AudioParagraph(id=segment_id, text=text)

        if current_subsection is not None:
            current_subsection.paragraphs.append(paragraph)
        else:
            paragraphs.append(paragraph)

    if current_subsection is not None:
        subsections.append(current_subsection)

    section = AudioSection(
        id=section_id,
        level=1,
        title=chapter_title,
        paragraphs=paragraphs,
        subsections=subsections,
    )

    return ChapterBuildResult(
        section=section,
        segment_ids_used=segment_ids_used,
        wiki_ids_cited=[],
    )


def build_glossary_from_wiki(
    wiki_entries: list[dict[str, Any]],
    *,
    chapter_text: str,
) -> tuple[list[PronunciationEntry], list[str]]:
    """Attach pronunciation hints for terms that appear in the chapter text.

    Glossary metadata is never applied as inline text substitution in emitters.
    """
    glossary: list[PronunciationEntry] = []
    wiki_ids_cited: list[str] = []
    haystack = chapter_text.lower()

    for entry in wiki_entries:
        if entry.get("status") != "canonical":
            continue

        label = str(entry.get("preferred_label") or "").strip()
        pronunciation = entry.get("pronunciation")

        if not label or not pronunciation:
            continue

        if label.lower() not in haystack:
            continue

        glossary.append(
            PronunciationEntry(
                term=label,
                alias=str(pronunciation),
            ),
        )
        wiki_ids_cited.append(str(entry["id"]))

    return glossary, wiki_ids_cited


def chapter_text_blob(chapter: dict[str, Any]) -> str:
    return "\n".join(_segment_text(segment) for segment in chapter.get("segments") or [])
