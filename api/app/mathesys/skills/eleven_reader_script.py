from __future__ import annotations

import json
import os
from typing import Any

from app.mathesys.chapter_grouping import (
    chapter_page_count,
    group_segments_into_chapters,
    split_chapters_into_volumes,
)
from app.mathesys.epub_builder import build_epub
from app.mathesys.skills.models import ElevenReaderScriptOutput, TransformedChapter
from app.services.openai_client import OpenAIClient

SYSTEM_PROMPT = """You transform source document text into clean, listenable prose for audio reading.

Rules:
- Preserve meaning and structure from the source.
- Use canonical wiki terminology exactly when wiki entries are provided.
- Expand acronyms on first use in each chapter: "Rules of Engagement (ROE)" then "ROE".
- Use pronunciation hints from wiki entries when helpful in plain text.
- Produce short paragraphs suitable for text-to-speech.
- Remove page headers, footers, page numbers, and OCR artifacts.
- Do not add commentary, study questions, or lesson framing.
- Return valid JSON only."""

USER_TEMPLATE = """Source metadata:
{source_metadata}

Canonical wiki entries:
{wiki_entries}

Chapter title: {chapter_title}

Source segments for this chapter:
{segments_json}

Return JSON:
{{
  "title": "chapter title string",
  "sections": [
    {{
      "heading": "optional section heading or null",
      "heading_level": 2,
      "paragraphs": ["paragraph text"]
    }}
  ],
  "wiki_ids_cited": ["wiki-id"],
  "segment_ids_used": ["segment-id"]
}}"""


class ElevenReaderScriptSkill:
    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
        max_pages_per_volume: int | None = None,
    ) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.max_pages_per_volume = max_pages_per_volume or int(
            os.getenv("ELEVEN_READER_MAX_PAGES", "500"),
        )

    def run(
        self,
        *,
        source_metadata: dict[str, Any],
        segments: list[dict[str, Any]],
        wiki_entries: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        grouped_chapters = group_segments_into_chapters(segments)
        volumes = split_chapters_into_volumes(
            grouped_chapters,
            max_pages=self.max_pages_per_volume,
        )

        wiki_context = [
            {
                "wiki_id": entry.get("id"),
                "preferred_label": entry.get("preferred_label"),
                "definition": entry.get("definition"),
                "pronunciation": entry.get("pronunciation"),
                "aliases": entry.get("aliases") or [],
            }
            for entry in wiki_entries
            if entry.get("status") == "canonical"
        ]

        generated_volumes: list[dict[str, Any]] = []
        token_usage: dict[str, int] = {}
        model = self.openai_client.model
        all_wiki_ids: set[str] = set()
        all_segment_ids: set[str] = set()

        metadata = self._extract_publication_metadata(source_metadata)
        base_title = metadata["title"]

        for volume_index, volume_chapters in enumerate(volumes, start=1):
            transformed_chapters: list[dict[str, Any]] = []

            for chapter in volume_chapters:
                transformed, execution = self._transform_chapter(
                    source_metadata=source_metadata,
                    wiki_context=wiki_context,
                    chapter=chapter,
                )
                transformed_chapters.append(transformed.model_dump())
                model = execution["model"]

                for key, value in execution["token_usage"].items():
                    token_usage[key] = token_usage.get(key, 0) + value

                all_wiki_ids.update(transformed.wiki_ids_cited)
                all_segment_ids.update(transformed.segment_ids_used)

            volume_title = self._volume_title(base_title, volume_index, len(volumes))
            epub_bytes = build_epub(
                title=volume_title,
                author=metadata["author"],
                identifier=metadata["identifier"],
                language=metadata["language"],
                publication_date=metadata["publication_date"],
                chapters=transformed_chapters,
            )
            pages_approx = sum(chapter_page_count(chapter) for chapter in volume_chapters)

            generated_volumes.append(
                {
                    "title": volume_title,
                    "epub_bytes": epub_bytes,
                    "chapters": transformed_chapters,
                    "pages_approx": pages_approx,
                    "part": volume_index,
                    "parts_total": len(volumes),
                },
            )

        return generated_volumes, {
            "model": model,
            "token_usage": token_usage,
            "wiki_ids_cited": sorted(all_wiki_ids),
            "segment_ids_used": sorted(all_segment_ids),
            "transformations": [
                "acronym_expansion",
                "header_footer_removal",
                "paragraph_reflow",
                "wiki_terminology",
            ],
        }

    def _transform_chapter(
        self,
        *,
        source_metadata: dict[str, Any],
        wiki_context: list[dict[str, Any]],
        chapter: dict[str, Any],
    ) -> tuple[TransformedChapter, dict[str, Any]]:
        compact_segments = [
            {
                "segment_id": segment.get("id"),
                "kind": segment.get("kind"),
                "text": segment.get("text"),
                "page": (segment.get("locator") or {}).get("page"),
            }
            for segment in chapter.get("segments", [])
        ]

        chapter_title = str(chapter.get("title") or "Chapter")

        result = self.openai_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                source_metadata=json.dumps(source_metadata, indent=2),
                wiki_entries=json.dumps(wiki_context, indent=2),
                chapter_title=chapter_title,
                segments_json=json.dumps(compact_segments, indent=2),
            ),
        )
        transformed = TransformedChapter.model_validate(result.content)

        return transformed, {
            "model": result.model,
            "token_usage": result.token_usage,
        }

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
