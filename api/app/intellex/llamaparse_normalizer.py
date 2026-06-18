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


def normalize_llamaparse_result(result: LlamaParseResult) -> ParsedDocument:
    lines: list[ParsedLine] = []

    for page in result.pages:
        for block_index, block in enumerate(_split_markdown_blocks(page.markdown)):
            first_line = block.splitlines()[0].strip()
            text, inferred_kind = _strip_heading_markers(first_line)

            if inferred_kind == "heading":
                line_text = text
                kind: LineKind | None = "heading"
            else:
                line_text = block
                kind = "paragraph"

            if not line_text:
                continue

            lines.append(
                ParsedLine(
                    line_id=f"p{page.page}-l{block_index}",
                    text=line_text,
                    page=page.page,
                    kind=kind,
                ),
            )

    page_count = max((line.page for line in lines), default=len(result.pages) or 0)

    if not page_count and result.pages:
        page_count = len(result.pages)

    return ParsedDocument(
        page_count=page_count,
        lines=lines,
        parser="llamaparse",
        job_id=result.job_id,
    )
