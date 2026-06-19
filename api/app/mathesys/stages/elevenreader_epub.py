from __future__ import annotations

from typing import Any

from app.mathesys.audio.audio_document_builder import AudioDocumentBuilder
from app.mathesys.audio.models import AudioSection
from app.mathesys.audio.segment_to_document import chapter_to_audio_section
from app.mathesys.chapter_grouping import (
    chapter_page_count,
    resolve_epub_chapters_from_segments,
)
from app.mathesys.stages.narration_base import NarrationStageBase, emit_epub_volume

_MISSING_CHAPTERS_ERROR = (
    "Run deconstruct-document first — no document_chapters for source."
)

ELEVENREADER_TRANSFORMATIONS = [
    "segment_chapter_boundaries",
    "elevenreader_simple_epub",
    "paragraph_preservation",
]


def chapter_rows_to_hydrated_chapters(
    chapter_rows: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not chapter_rows:
        raise RuntimeError(_MISSING_CHAPTERS_ERROR)

    return resolve_epub_chapters_from_segments(segments)


def chapter_rows_to_audio_sections(
    chapter_rows: list[dict[str, Any]],
    segments: list[dict[str, Any]],
) -> list[AudioSection]:
    hydrated_chapters = chapter_rows_to_hydrated_chapters(chapter_rows, segments)

    return [
        chapter_to_audio_section(chapter).section
        for chapter in hydrated_chapters
    ]


def build_single_elevenreader_epub(
    *,
    source_metadata: dict[str, Any],
    segments: list[dict[str, Any]],
    chapter_rows: list[dict[str, Any]] | None,
    wiki_entries: list[dict[str, Any]] | None = None,
    audience: str | None = None,
    narration_base: NarrationStageBase | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not segments:
        raise RuntimeError("No NDR segments available for narration.")

    base = narration_base or NarrationStageBase()
    hydrated_chapters = chapter_rows_to_hydrated_chapters(chapter_rows or [], segments)
    metadata = base._extract_publication_metadata(source_metadata)
    base_title = metadata["title"]
    chapter_titles = [str(chapter.get("title") or "Untitled Section") for chapter in hydrated_chapters]

    document, build_execution = base.document_builder.build_document(
        title=base_title,
        author=metadata["author"],
        source_metadata=source_metadata,
        chapters=hydrated_chapters,
        wiki_entries=wiki_entries or [],
        language=metadata["language"],
        audience=audience,
    )

    emitted, validation = emit_epub_volume()(document, metadata)

    if not validation.valid:
        raise RuntimeError(
            "Narration output failed validation: " + "; ".join(validation.errors),
        )

    pages_approx = sum(chapter_page_count(chapter) for chapter in hydrated_chapters)

    volume = {
        "title": base_title,
        "pages_approx": pages_approx,
        "part": 1,
        "parts_total": 1,
        "chapter_count": len(hydrated_chapters),
        "chapter_titles": chapter_titles,
        "audio_document": document.model_dump(),
        "validation": validation.model_dump(),
        **emitted,
    }

    return [volume], {
        "model": build_execution["model"],
        "token_usage": build_execution["token_usage"],
        "wiki_ids_cited": [],
        "segment_ids_used": build_execution["segment_ids_used"],
        "transformations": ELEVENREADER_TRANSFORMATIONS,
        "warnings": validation.warnings,
        "prepare": source_metadata.get("prepare"),
        "chapter_count": len(hydrated_chapters),
        "chapter_titles": chapter_titles,
    }
