"""Deterministic read-aloud content filter.

Strips front/back matter chapters and per-segment clutter (page numbers, TOC
dot-leaders, running headers/footers, figure/table captions, bare
citation/footnote markers, boilerplate) from NDR segments before they are
grouped into chapters and narrated. The goal is for every downstream audio
output (EPUB EBook, SSML, ElevenLabs structured text) to contain only the
actual body content a listener wants to hear.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

# Headings whose section is non-body matter that should never be narrated.
_FRONT_BACK_MATTER_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p)
    for p in (
        r"^(table of )?contents$",
        r"^contents$",
        r"^list of (figures|tables|illustrations|abbreviations|acronyms|maps|plates)$",
        r"^master list of (figures|tables|illustrations|maps|plates)$",
        r"^(index|subject index|author index)$",
        r"^(bibliography|references|works cited|further reading|sources)$",
        r"^(notes|endnotes|footnotes)$",
        r"^(appendix|appendices)\b",
        r"^(acknowledge?ments?)$",
        r"^(copyright|copyright notice)$",
        r"^(dedication)$",
        r"^(foreword|forward)$",
        r"^(preface)$",
        r"^(about the author|about the authors|author biography)$",
        r"^(glossary|glossary of terms|terms and definitions|definitions)$",
        r"^(acronyms|acronyms and abbreviations|abbreviations|list of abbreviations)$",
        r"^(synopsis|executive summary)$",
        r"^(distribution statement|disclaimer|distribution restriction)\b",
        r"^(title page|half title|colophon|imprint)$",
        r"^(errata)$",
        r"^(record of changes|change record|summary of changes)$",
    )
]

_PAGE_NUMBER_RE = re.compile(r"^\s*(page\s+)?[0-9ivxlcdm]{1,6}\s*$", re.IGNORECASE)
_DOT_LEADER_RE = re.compile(r"\.{4,}\s*\d+\s*$")
_CAPTION_RE = re.compile(
    r"^\s*(figure|fig\.?|table|tbl\.?|plate|exhibit|chart|diagram|illustration|map|photo)\s+"
    r"(\d+|[ivxlcdm]+)([.\-:]|\s|$)",
    re.IGNORECASE,
)
_MARKER_ONLY_RE = re.compile(r"^\s*[\[\(]?\d{1,4}[\]\).]?\s*$")
_BLANK_PAGE_RE = re.compile(r"this page (is )?intentionally left blank", re.IGNORECASE)
_URL_DOI_ONLY_RE = re.compile(
    r"^\s*(https?://\S+|doi:\s*\S+|www\.\S+)\s*$",
    re.IGNORECASE,
)

# A short non-heading line is a running-header/footer candidate when it repeats
# verbatim across at least this many distinct pages.
_RUNNING_HEADER_MIN_PAGES = 4
_RUNNING_HEADER_MAX_CHARS = 90


def _normalize_heading(text: str) -> str:
    cleaned = text.strip().lower()
    # Drop leading chapter/section numbering ("Chapter 3:", "1.", "Section II -")
    cleaned = re.sub(
        r"^(chapter|section|part|annex|appendix|unit|lesson)\s+[0-9ivxlcdm]+\s*[:.\-]?\s*",
        "",
        cleaned,
    )
    cleaned = re.sub(r"^[0-9ivxlcdm]+\s*[:.\-]\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .:-—–")
    return cleaned


def _is_front_back_matter_heading(text: str) -> bool:
    normalized = _normalize_heading(text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _FRONT_BACK_MATTER_PATTERNS)


def _segment_page(segment: dict[str, Any]) -> Any:
    locator = segment.get("locator") or {}
    return locator.get("page")


def _normalized_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _running_header_texts(segments: list[dict[str, Any]]) -> set[str]:
    pages_by_text: dict[str, set[Any]] = defaultdict(set)

    for segment in segments:
        text = str(segment.get("text") or "").strip()
        if not text or len(text) > _RUNNING_HEADER_MAX_CHARS:
            continue
        page = _segment_page(segment)
        if page is None:
            continue
        pages_by_text[_normalized_line(text)].add(page)

    return {
        text
        for text, pages in pages_by_text.items()
        if len(pages) >= _RUNNING_HEADER_MIN_PAGES
    }


def _clutter_reason(text: str, running_headers: set[str]) -> str | None:
    stripped = text.strip()

    if not stripped:
        return "empty"
    if _BLANK_PAGE_RE.search(stripped):
        return "blank_page_notice"
    if _PAGE_NUMBER_RE.match(stripped):
        return "page_number"
    if _DOT_LEADER_RE.search(stripped):
        return "toc_dot_leader"
    if _CAPTION_RE.match(stripped):
        return "figure_table_caption"
    if _MARKER_ONLY_RE.match(stripped):
        return "citation_marker"
    if _URL_DOI_ONLY_RE.match(stripped):
        return "bare_url_or_doi"
    if _normalized_line(stripped) in running_headers:
        return "running_header_footer"

    return None


def filter_segments_for_audio(
    segments: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return body-only segments plus a report of what was removed."""

    if not segments:
        return [], {
            "dropped_chapters": [],
            "dropped_segment_count": 0,
            "kept_segment_count": 0,
            "reasons": {},
        }

    running_headers = _running_header_texts(segments)
    kept: list[dict[str, Any]] = []
    dropped_chapters: list[str] = []
    reasons: Counter[str] = Counter()
    skipping_chapter = False

    for segment in segments:
        is_heading = segment.get("kind") == "heading"
        text = str(segment.get("text") or "")

        if is_heading:
            if _is_front_back_matter_heading(text):
                skipping_chapter = True
                dropped_chapters.append(text.strip())
                reasons["front_back_matter_chapter"] += 1
                continue
            if _normalized_line(text.strip()) in running_headers:
                reasons["running_header_footer"] += 1
                continue
            skipping_chapter = False
            kept.append(segment)
            continue

        if skipping_chapter:
            reasons["front_back_matter_body"] += 1
            continue

        reason = _clutter_reason(text, running_headers)
        if reason is not None:
            reasons[reason] += 1
            continue

        kept.append(segment)

    report = {
        "dropped_chapters": dropped_chapters,
        "dropped_segment_count": len(segments) - len(kept),
        "kept_segment_count": len(kept),
        "reasons": dict(reasons),
    }

    return kept, report
