from __future__ import annotations

import os
from typing import Any, Callable

from app.mathesys.audio.audio_document_builder import AudioDocumentBuilder
from app.mathesys.chapter_grouping import (
    chapter_page_count,
    resolve_chapters_for_source,
    split_chapters_into_volumes,
)
from app.mathesys.epub_builder import build_epub
from app.mathesys.audio.emitters.epub_emitter import (
    audio_document_to_epub_chapters,
    epub_chapters_to_builder_format,
)
from app.mathesys.audio.models import AudioDocument, ElevenLabsMode, ValidationResult


class NarrationSkillBase:
    def __init__(
        self,
        *,
        document_builder: AudioDocumentBuilder | None = None,
        max_pages_per_volume: int | None = None,
    ) -> None:
        self.document_builder = document_builder or AudioDocumentBuilder()
        self.max_pages_per_volume = max_pages_per_volume or int(
            os.getenv("ELEVEN_READER_MAX_PAGES", "500"),
        )

    @property
    def _build_model_label(self) -> str:
        return "deterministic-passthrough"

    def _extract_publication_metadata(self, source_metadata: dict[str, Any]) -> dict[str, Any]:
        research = source_metadata.get("research") or {}

        if not isinstance(research, dict):
            research = {}

        title = str(research.get("title") or source_metadata.get("title") or "BriefWorks Script")
        authors = research.get("authors")

        if isinstance(authors, list) and authors:
            author = str(authors[0])
        elif research.get("issuing_authority"):
            author = str(research.get("issuing_authority"))
        else:
            author = "BriefWorks"

        identifier = research.get("identifier")
        publication_date = research.get("publication_date_public") or research.get(
            "publication_date_in_document",
        )

        return {
            "title": title,
            "author": author,
            "identifier": str(identifier) if identifier else None,
            "publication_date": str(publication_date) if publication_date else None,
            "language": "en",
        }

    def _volume_title(self, base_title: str, part: int, parts_total: int) -> str:
        if parts_total <= 1:
            return base_title

        return f"{base_title} — Part {part} of {parts_total}"

    def run_volumes(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
        chapter_rows: list[dict[str, Any]] | None = None,
        emit_volume: Callable[
            [AudioDocument, dict[str, Any]],
            tuple[dict[str, Any], ValidationResult],
        ],
        transformations: list[str],
        audience: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not segments:
            raise RuntimeError("No NDR segments available for narration.")

        grouped_chapters = resolve_chapters_for_source(
            chapter_rows=chapter_rows or [],
            segments=segments,
        )
        volumes = split_chapters_into_volumes(
            grouped_chapters,
            max_pages=self.max_pages_per_volume,
        )

        metadata = self._extract_publication_metadata(source_metadata)
        base_title = metadata["title"]
        generated_volumes: list[dict[str, Any]] = []
        token_usage: dict[str, int] = {}
        model = self._build_model_label
        all_wiki_ids: set[str] = set()
        all_segment_ids: set[str] = set()
        all_warnings: list[str] = []

        for volume_index, volume_chapters in enumerate(volumes, start=1):
            document, build_execution = self.document_builder.build_document(
                title=base_title,
                author=metadata["author"],
                source_metadata=source_metadata,
                chapters=volume_chapters,
                wiki_entries=wiki_entries,
                language=metadata["language"],
                audience=audience,
            )
            model = build_execution["model"]
            all_segment_ids.update(build_execution["segment_ids_used"])
            all_wiki_ids.update(build_execution["wiki_ids_cited"])

            for key, value in build_execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            emitted, validation = emit_volume(document, metadata)
            all_warnings.extend(validation.warnings)

            if not validation.valid:
                raise RuntimeError(
                    "Narration output failed validation: " + "; ".join(validation.errors),
                )

            volume_title = self._volume_title(base_title, volume_index, len(volumes))
            pages_approx = sum(chapter_page_count(chapter) for chapter in volume_chapters)

            generated_volumes.append(
                {
                    "title": volume_title,
                    "pages_approx": pages_approx,
                    "part": volume_index,
                    "parts_total": len(volumes),
                    "audio_document": document.model_dump(),
                    "validation": validation.model_dump(),
                    **emitted,
                },
            )

        return generated_volumes, {
            "model": model,
            "token_usage": token_usage,
            "wiki_ids_cited": sorted(all_wiki_ids),
            "segment_ids_used": sorted(all_segment_ids),
            "transformations": transformations,
            "warnings": all_warnings,
            "prepare": source_metadata.get("prepare"),
        }


def emit_epub_volume() -> Callable[
    [AudioDocument, dict[str, Any]],
    tuple[dict[str, Any], ValidationResult],
]:
    def _emit(document: AudioDocument, metadata: dict[str, Any]) -> tuple[dict[str, Any], ValidationResult]:
        chapters = audio_document_to_epub_chapters(document, target="elevenreader_app_epub")
        epub_bytes = build_epub(
            title=document.title,
            author=metadata["author"],
            identifier=metadata["identifier"],
            language=metadata["language"],
            publication_date=metadata["publication_date"],
            chapters=epub_chapters_to_builder_format(chapters),
        )

        return (
            {
                "epub_bytes": epub_bytes,
                "chapters": [chapter.model_dump() for chapter in chapters],
            },
            ValidationResult(valid=True),
        )

    return _emit


def emit_ssml_volume() -> Callable[[AudioDocument, dict[str, Any]], tuple[dict[str, Any], ValidationResult]]:
    from app.mathesys.audio.emitters.speechify_ssml import emit_speechify_ssml
    from app.mathesys.audio.validation.validate_ssml import validate_ssml

    def _emit(document: AudioDocument, _metadata: dict[str, Any]) -> tuple[dict[str, Any], ValidationResult]:
        output = emit_speechify_ssml(document)
        validation = validate_ssml(output)

        return (
            {
                "ssml": output.ssml,
                "section_count": output.section_count,
                "estimated_character_count": output.estimated_character_count,
            },
            validation,
        )

    return _emit


def emit_eleven_labs_volume(
    *,
    mode: ElevenLabsMode = "expressive_v3",
    model_id: str | None = None,
) -> Callable[[AudioDocument, dict[str, Any]], tuple[dict[str, Any], ValidationResult]]:
    from app.mathesys.audio.emitters.eleven_labs_structured_text import (
        emit_eleven_labs_structured_text,
    )
    from app.mathesys.audio.validation.validate_eleven_labs_text import validate_eleven_labs_text

    def _emit(document: AudioDocument, _metadata: dict[str, Any]) -> tuple[dict[str, Any], ValidationResult]:
        output = emit_eleven_labs_structured_text(document, mode=mode, model_id=model_id)
        validation = validate_eleven_labs_text(output)

        return (
            {"structured_text": output.model_dump()},
            validation,
        )

    return _emit
