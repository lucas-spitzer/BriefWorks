from __future__ import annotations

import json
from typing import Any

from app.mathesys.audio.models import AudioDocument, AudioSection, ChapterBuildResult, PronunciationEntry
from app.mathesys.audio.prompts import (
    CANONICAL_AUDIO_DOCUMENT_SYSTEM_PROMPT,
    CANONICAL_AUDIO_DOCUMENT_USER_TEMPLATE,
)
from app.mathesys.audio.segment_text import infer_source_type, segments_to_extracted_text
from app.services.openai_client import OpenAIClient


def build_wiki_context(wiki_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
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


class AudioDocumentBuilder:
    def __init__(self, *, openai_client: OpenAIClient | None = None) -> None:
        self.openai_client = openai_client or OpenAIClient()

    def build_chapter_section(
        self,
        *,
        source_metadata: dict[str, Any],
        chapter: dict[str, Any],
        wiki_entries: list[dict[str, Any]],
        language: str = "en-US",
        audience: str | None = None,
    ) -> tuple[ChapterBuildResult, dict[str, Any]]:
        segments = chapter.get("segments") or []
        chapter_title = str(chapter.get("title") or "Chapter")
        extracted_text = segments_to_extracted_text(segments)

        result = self.openai_client.complete_json(
            system_prompt=CANONICAL_AUDIO_DOCUMENT_SYSTEM_PROMPT,
            user_prompt=CANONICAL_AUDIO_DOCUMENT_USER_TEMPLATE.format(
                source_type=infer_source_type(source_metadata),
                language=language,
                audience=audience or "general",
                wiki_entries=json.dumps(build_wiki_context(wiki_entries), indent=2),
                chapter_title=chapter_title,
                extracted_text=extracted_text,
            ),
        )

        payload = result.content
        section = AudioSection.model_validate(payload["section"])
        glossary = [
            PronunciationEntry.model_validate(entry)
            for entry in payload.get("glossary") or []
        ]

        build_result = ChapterBuildResult(
            section=section,
            segment_ids_used=[str(value) for value in payload.get("segment_ids_used") or []],
            wiki_ids_cited=[str(value) for value in payload.get("wiki_ids_cited") or []],
        )

        return build_result, {
            "model": result.model,
            "token_usage": result.token_usage,
            "glossary": glossary,
        }

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
        sections: list[AudioSection] = []
        glossary: list[PronunciationEntry] = []
        segment_ids: set[str] = set()
        wiki_ids: set[str] = set()
        token_usage: dict[str, int] = {}
        model = self.openai_client.model

        for chapter in chapters:
            build_result, execution = self.build_chapter_section(
                source_metadata=source_metadata,
                chapter=chapter,
                wiki_entries=wiki_entries,
                language=language,
                audience=audience,
            )
            sections.append(build_result.section)
            segment_ids.update(build_result.segment_ids_used)
            wiki_ids.update(build_result.wiki_ids_cited)
            glossary.extend(execution.get("glossary") or [])
            model = execution["model"]

            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

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
            "model": model,
            "token_usage": token_usage,
            "segment_ids_used": sorted(segment_ids),
            "wiki_ids_cited": sorted(wiki_ids),
        }
