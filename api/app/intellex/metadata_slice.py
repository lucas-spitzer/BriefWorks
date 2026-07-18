from __future__ import annotations

import re

from app.intellex.models import ParsedDocument, ParsedLine

_PREFACE_HEADING_RE = re.compile(
    r"^(preface|foreword|introduction|executive\s+summary|purpose"
    r"|abstract|summary|overview|scope"
    r"|about\s+this\s+(document|publication|report|paper|manual|guide|book|standard))\b",
    re.IGNORECASE,
)
_TOC_HEADING_RE = re.compile(
    r"^(table\s+of\s+contents|contents)\b",
    re.IGNORECASE,
)

_COVER_MAX_CHARS = 4_000
_PREFACE_MAX_CHARS = 6_000
_TOC_MAX_CHARS = 3_000
_COVER_MAX_PAGE = 2
_PREFACE_MAX_PAGE = 10
_TOC_MAX_PAGE = 8
_REMAINDER_MAX_PAGE = 5


def build_metadata_slice(
    document: ParsedDocument,
    *,
    max_chars: int = 12_000,
    max_pages: int = 5,
) -> str:
    """Return early-page text for bibliographic metadata extraction."""
    del max_pages
    slices = build_source_research_slices(document, max_chars=max_chars)
    parts = [slices[key] for key in ("cover", "preface", "toc", "remainder") if slices[key]]
    return "\n\n".join(parts).strip()


def build_source_research_slices(
    document: ParsedDocument,
    *,
    max_chars: int = 16_000,
) -> dict[str, str]:
    """Return labeled early-document sections for source profile extraction."""
    if not document.lines:
        return {"cover": "", "preface": "", "toc": "", "remainder": ""}

    cover_budget = min(_COVER_MAX_CHARS, max(0, int(max_chars * 0.25)))
    preface_budget = min(_PREFACE_MAX_CHARS, max(0, int(max_chars * 0.375)))
    toc_budget = min(_TOC_MAX_CHARS, max(0, int(max_chars * 0.1875)))

    used_indices: set[int] = set()

    cover, cover_indices = _collect_page_lines(
        document.lines,
        max_page=_COVER_MAX_PAGE,
        max_chars=cover_budget,
    )
    used_indices.update(cover_indices)

    preface, preface_indices = _collect_section_after_heading(
        document.lines,
        heading_match=_PREFACE_HEADING_RE,
        max_chars=preface_budget,
        max_page=_PREFACE_MAX_PAGE,
        stop_at_next_heading=True,
    )
    used_indices.update(preface_indices)

    toc, toc_indices = _collect_section_after_heading(
        document.lines,
        heading_match=_TOC_HEADING_RE,
        max_chars=toc_budget,
        max_page=_TOC_MAX_PAGE,
        stop_at_next_heading=True,
    )
    used_indices.update(toc_indices)

    remainder_budget = max(0, max_chars - len(cover) - len(preface) - len(toc))
    remainder, _ = _collect_remainder(
        document.lines,
        used_indices=used_indices,
        max_page=_REMAINDER_MAX_PAGE,
        max_chars=remainder_budget,
    )

    return {
        "cover": cover,
        "preface": preface,
        "toc": toc,
        "remainder": remainder,
    }


def _is_heading(line: ParsedLine) -> bool:
    if line.kind == "heading":
        return True
    text = line.text.strip()
    return bool(text) and len(text) <= 80 and text == text.upper()


def _heading_matches(line: ParsedLine, pattern: re.Pattern[str]) -> bool:
    text = line.text.strip()
    if not text:
        return False
    if line.kind == "heading":
        return bool(pattern.match(text))
    return bool(pattern.match(text)) or (
        _is_heading(line) and bool(pattern.match(text))
    )


def _collect_page_lines(
    lines: list[ParsedLine],
    *,
    max_page: int,
    max_chars: int,
) -> tuple[str, set[int]]:
    chunks: list[str] = []
    indices: set[int] = set()
    total_chars = 0

    for index, line in enumerate(lines):
        if line.page > max_page:
            continue
        if total_chars >= max_chars:
            break
        chunks.append(line.text)
        indices.add(index)
        total_chars += len(line.text) + 1

    return "\n".join(chunks).strip(), indices


def _collect_section_after_heading(
    lines: list[ParsedLine],
    *,
    heading_match: re.Pattern[str],
    max_chars: int,
    max_page: int | None = None,
    stop_at_next_heading: bool = False,
) -> tuple[str, set[int]]:
    start_index: int | None = None

    for index, line in enumerate(lines):
        if max_page is not None and line.page > max_page:
            break
        if _heading_matches(line, heading_match):
            start_index = index
            break

    if start_index is None:
        return "", set()

    chunks: list[str] = []
    indices: set[int] = set()
    total_chars = 0

    for index, line in enumerate(lines[start_index:], start=start_index):
        if max_page is not None and line.page > max_page:
            break
        if stop_at_next_heading and index != start_index and _is_heading(line):
            break
        if total_chars >= max_chars:
            break
        chunks.append(line.text)
        indices.add(index)
        total_chars += len(line.text) + 1

    return "\n".join(chunks).strip(), indices


def _collect_remainder(
    lines: list[ParsedLine],
    *,
    used_indices: set[int],
    max_page: int,
    max_chars: int,
) -> tuple[str, set[int]]:
    if max_chars <= 0:
        return "", set()

    chunks: list[str] = []
    indices: set[int] = set()
    total_chars = 0

    for index, line in enumerate(lines):
        if line.page > max_page:
            continue
        if index in used_indices:
            continue
        if line.page <= _COVER_MAX_PAGE:
            continue
        if total_chars >= max_chars:
            break
        chunks.append(line.text)
        indices.add(index)
        total_chars += len(line.text) + 1

    return "\n".join(chunks).strip(), indices
