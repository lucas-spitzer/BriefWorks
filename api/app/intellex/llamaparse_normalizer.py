from __future__ import annotations

import re

from app.intellex.models import LineKind, ParsedDocument, ParsedLine
from app.services.llamaparse_client import LlamaParseResult

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_BLANK_LINE_RE = re.compile(r"^\s*$")


def _strip_heading_markers(text: str) -> tuple[str, LineKind | None]:
    match = _HEADING_RE.match(text.strip())

    if match:
        return match.group(2).strip(), "heading"

    return text.strip(), None


def _split_markdown_blocks(markdown: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []

    for raw_line in markdown.splitlines():
        if _BLANK_LINE_RE.match(raw_line):
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue

        if _HEADING_RE.match(raw_line.strip()) and current:
            blocks.append("\n".join(current).strip())
            current = [raw_line]
            continue

        current.append(raw_line)

    if current:
        blocks.append("\n".join(current).strip())

    return [block for block in blocks if block]


def _lines_from_block(
    block: str,
    *,
    page: int,
    line_index: int,
) -> tuple[list[ParsedLine], int]:
    block_lines = block.splitlines()
    first_line = block_lines[0].strip()
    heading_text, inferred_kind = _strip_heading_markers(first_line)

    if inferred_kind == "heading":
        lines: list[ParsedLine] = [
            ParsedLine(
                line_id=f"p{page}-l{line_index}",
                text=heading_text,
                page=page,
                kind="heading",
            ),
        ]
        line_index += 1

        remainder = "\n".join(block_lines[1:]).strip()

        for part in _split_markdown_blocks(remainder):
            cleaned = part.strip()

            if not cleaned:
                continue

            lines.append(
                ParsedLine(
                    line_id=f"p{page}-l{line_index}",
                    text=cleaned,
                    page=page,
                    kind="paragraph",
                ),
            )
            line_index += 1

        return lines, line_index

    return [
        ParsedLine(
            line_id=f"p{page}-l{line_index}",
            text=block.strip(),
            page=page,
            kind="paragraph",
        ),
    ], line_index + 1


def normalize_llamaparse_result(result: LlamaParseResult) -> ParsedDocument:
    lines: list[ParsedLine] = []

    for page in result.pages:
        line_index = 0

        for block in _split_markdown_blocks(page.markdown):
            block_lines, line_index = _lines_from_block(
                block,
                page=page.page,
                line_index=line_index,
            )
            lines.extend(block_lines)

    page_count = max((line.page for line in lines), default=len(result.pages) or 0)

    if not page_count and result.pages:
        page_count = len(result.pages)

    return ParsedDocument(
        page_count=page_count,
        lines=lines,
        parser="llamaparse",
        job_id=result.job_id,
    )
