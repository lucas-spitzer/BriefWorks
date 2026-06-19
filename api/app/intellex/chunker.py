from __future__ import annotations

import uuid
from typing import Any

from app.intellex.heading_classification import is_doctrinal_subsection_heading
from app.intellex.models import ParsedDocument, ParsedLine
from app.intellex.pdf_parser import classify_lines


def _line_locator(line: ParsedLine, *, char_start: int, char_end: int) -> dict[str, Any]:
    locator: dict[str, Any] = {
        "page": line.page,
        "char_start": char_start,
        "char_end": char_end,
    }

    if line.bbox:
        locator["bbox"] = line.bbox

    if line.font_size:
        locator["font_size"] = line.font_size

    return locator


def _flush_paragraph(
    *,
    parts: list[ParsedLine],
    segments: list[dict[str, Any]],
    sequence_index: int,
) -> int:
    if not parts:
        return sequence_index

    text = " ".join(part.text for part in parts)
    locator = _line_locator(
        parts[0],
        char_start=0,
        char_end=len(text),
    )
    locator["page_end"] = parts[-1].page

    segments.append(
        {
            "id": str(uuid.uuid4()),
            "sequence_index": sequence_index,
            "kind": "paragraph",
            "text": text,
            "locator": locator,
        },
    )
    return sequence_index + 1


def _classify_line(document: ParsedDocument, line: ParsedLine) -> str:
    if line.kind == "heading":
        return "heading"

    if line.kind == "paragraph":
        return "paragraph"

    classified = classify_lines(
        ParsedDocument(page_count=document.page_count, lines=[line], parser=document.parser),
    )

    if classified:
        return classified[0][0]

    return "paragraph"


def _expand_subsection_headings_in_segments(
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Promote ALL-CAPS subsection titles that were merged into paragraph blocks."""
    expanded: list[dict[str, Any]] = []

    for segment in segments:
        text = str(segment.get("text") or "")

        if segment.get("kind") != "paragraph" or "\n" not in text:
            expanded.append(segment)
            continue

        first_line = text.split("\n", 1)[0].strip()

        if not is_doctrinal_subsection_heading(first_line):
            expanded.append(segment)
            continue

        remainder = text.split("\n", 1)[1].strip()
        expanded.append(
            {
                **segment,
                "kind": "heading",
                "text": first_line,
            },
        )

        if remainder:
            expanded.append(
                {
                    **segment,
                    "id": str(uuid.uuid4()),
                    "kind": "paragraph",
                    "text": remainder,
                },
            )

    return expanded


def build_ndr_segments(document: ParsedDocument) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    paragraph_parts: list[ParsedLine] = []
    sequence_index = 0

    for line in document.lines:
        kind = _classify_line(document, line)

        if kind == "heading":
            sequence_index = _flush_paragraph(
                parts=paragraph_parts,
                segments=segments,
                sequence_index=sequence_index,
            )
            paragraph_parts = []

            segments.append(
                {
                    "id": str(uuid.uuid4()),
                    "sequence_index": sequence_index,
                    "kind": "heading",
                    "text": line.text,
                    "locator": _line_locator(line, char_start=0, char_end=len(line.text)),
                },
            )
            sequence_index += 1
            continue

        if paragraph_parts and paragraph_parts[-1].page != line.page:
            sequence_index = _flush_paragraph(
                parts=paragraph_parts,
                segments=segments,
                sequence_index=sequence_index,
            )
            paragraph_parts = []

        paragraph_parts.append(line)

    _flush_paragraph(
        parts=paragraph_parts,
        segments=segments,
        sequence_index=sequence_index,
    )

    return _expand_subsection_headings_in_segments(segments)
