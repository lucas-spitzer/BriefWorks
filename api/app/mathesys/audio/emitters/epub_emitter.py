from __future__ import annotations

import html
from typing import Any, Literal

from app.mathesys.audio.models import AudioDocument, AudioSection, EpubChapterOutput

EpubTarget = Literal["elevenreader_app_epub"]


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _heading_tag(level: int) -> str:
    return f"h{min(max(level, 1), 3)}"


def _section_to_xhtml_parts(
    section: AudioSection,
    *,
    target: EpubTarget,
    include_top_heading: bool = True,
) -> list[str]:
    parts: list[str] = []

    if include_top_heading:
        heading_level = 1 if target == "elevenreader_app_epub" else section.level
        parts.append(
            f"<{_heading_tag(heading_level)}>{_escape(section.title)}</{_heading_tag(heading_level)}>",
        )

    for paragraph in section.paragraphs:
        cleaned = paragraph.text.strip()

        if cleaned:
            parts.append(f"<p>{_escape(cleaned)}</p>")

    for subsection in section.subsections:
        parts.append(
            f"<{_heading_tag(subsection.level)}>{_escape(subsection.title)}</{_heading_tag(subsection.level)}>",
        )

        for paragraph in subsection.paragraphs:
            cleaned = paragraph.text.strip()

            if cleaned:
                parts.append(f"<p>{_escape(cleaned)}</p>")

        for nested in subsection.subsections:
            parts.extend(
                _section_to_xhtml_parts(
                    nested,
                    target=target,
                    include_top_heading=True,
                ),
            )

    return parts


def sections_to_xhtml(
    sections: list[AudioSection],
    *,
    target: EpubTarget,
) -> str:
    parts: list[str] = []

    for section in sections:
        parts.extend(_section_to_xhtml_parts(section, target=target))

    return "".join(parts)


def audio_document_to_epub_chapters(
    document: AudioDocument,
    *,
    target: EpubTarget,
) -> list[EpubChapterOutput]:
    chapters: list[EpubChapterOutput] = []

    for index, section in enumerate(document.sections, start=1):
        xhtml_body = "".join(
            _section_to_xhtml_parts(section, target=target),
        )
        chapters.append(
            EpubChapterOutput(
                id=section.id,
                title=section.title,
                level=section.level,
                filename=f"chapter-{index:03d}.xhtml",
                xhtml=xhtml_body,
                chapter_start=target == "elevenreader_app_epub",
            ),
        )

    return chapters


def epub_chapters_to_builder_format(
    chapters: list[EpubChapterOutput],
) -> list[dict[str, Any]]:
    builder_chapters: list[dict[str, Any]] = []

    for chapter in chapters:
        builder_chapters.append(
            {
                "title": chapter.title,
                "xhtml_body": chapter.xhtml,
            },
        )

    return builder_chapters
