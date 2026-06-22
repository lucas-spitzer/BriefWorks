"""Chunk-from-structure: turn the Book model into ndr_segments + document_chapters.

In the new pipeline the chapter/section structure is already known before
chunking, so this single deterministic step produces both the NDR segments
(consumed by source-research-adjacent steps and extract-knowledge) and the
document_chapters rows (consumed by extract-knowledge), taking over the chapter
grouping that the removed deconstruct-document step used to do via an LLM.

ndr_segments carry PLAIN text (markdown emphasis flattened) so they stay clean
for downstream LLM extraction; the markdown-faithful copy lives in the persisted
Structure artifact, which the Create EBook stage renders for italics/bold.

Each top-level chapter becomes one document_chapters row (level 1) whose
segment_ids are, in order: the chapter-title heading, intro paragraphs, then for
each section its heading followed by its body paragraphs. That ordering lets the
existing chapter->audio/epub reconstruction recover the H1/H2 hierarchy.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from app.intellex.structuring.models import Book

_EMPH_RE = re.compile(r"\*{1,3}(.+?)\*{1,3}", re.DOTALL)
_SUP_TAG_RE = re.compile(r"<sup>.*?</sup>", re.IGNORECASE | re.DOTALL)


def flatten_markdown(md: str) -> str:
    """Drop inline markdown emphasis and any stray sup tags for clean segment text."""
    text = _SUP_TAG_RE.sub("", md)
    text = _EMPH_RE.sub(r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _segment(seq: int, kind: str, text: str, page: int | None) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "sequence_index": seq,
        "kind": kind,
        "text": text,
        "locator": {"page": page},
    }


def build_segments_and_chapters(
    book: Book,
    *,
    source_id: str,
    workspace_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (ndr_segment_rows, document_chapter_rows)."""
    segments: list[dict[str, Any]] = []
    chapters: list[dict[str, Any]] = []
    seq = 0

    for chapter_index, chapter in enumerate(book.chapters):
        chapter_segment_ids: list[str] = []

        head = _segment(seq, "heading", chapter.title, chapter.page)
        seq += 1
        segments.append(head)
        chapter_segment_ids.append(head["id"])

        for para in chapter.intro:
            text = flatten_markdown(para.md)
            if not text:
                continue
            row = _segment(seq, "paragraph", text, para.page)
            seq += 1
            segments.append(row)
            chapter_segment_ids.append(row["id"])

        for section in chapter.sections:
            sec_head = _segment(seq, "heading", section.title, section.page)
            seq += 1
            segments.append(sec_head)
            chapter_segment_ids.append(sec_head["id"])
            for para in section.body:
                text = flatten_markdown(para.md)
                if not text:
                    continue
                row = _segment(seq, "paragraph", text, para.page)
                seq += 1
                segments.append(row)
                chapter_segment_ids.append(row["id"])

        chapters.append(
            {
                "id": str(uuid.uuid4()),
                "source_id": source_id,
                "workspace_id": workspace_id,
                "sequence_index": chapter_index,
                "title": chapter.title,
                "level": 1,
                "segment_ids": chapter_segment_ids,
            }
        )

    # attach source/workspace to segment rows (matches chunk_parsed_document shape)
    for row in segments:
        row["source_id"] = source_id
        row["workspace_id"] = workspace_id

    return segments, chapters
