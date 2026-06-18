"""Deterministic line-level filter for prepare-document.

Removes front/back matter sections and per-line clutter before and after the
LLM prepare pass so only chapter/section headings and learning body text remain.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from app.intellex.content_filter import (
    _BLANK_PAGE_RE,
    _CAPTION_RE,
    _DOT_LEADER_RE,
    _MARKER_ONLY_RE,
    _PAGE_NUMBER_RE,
    _RUNNING_HEADER_MAX_CHARS,
    _RUNNING_HEADER_MIN_PAGES,
    _URL_DOI_ONLY_RE,
    _is_front_back_matter_heading,
    _normalized_line,
)

from app.intellex.models import ParsedDocument, ParsedLine

_DISTRIBUTION_LINE_RE = re.compile(
    r"^\s*distribution\s+statement\b",
    re.IGNORECASE,
)

_is_forbidden_heading = _is_front_back_matter_heading


def _is_heading_line(line: ParsedLine) -> bool:
    return (line.kind or "paragraph") == "heading"


def _running_header_texts(lines: list[ParsedLine]) -> set[str]:
    pages_by_text: dict[str, set[int]] = defaultdict(set)

    for line in lines:
        if _is_heading_line(line):
            continue
        text = line.text.strip()
        if not text or len(text) > _RUNNING_HEADER_MAX_CHARS:
            continue
        pages_by_text[_normalized_line(text)].add(line.page)

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
    if _DISTRIBUTION_LINE_RE.match(stripped):
        return "distribution_statement"
    if _normalized_line(stripped) in running_headers:
        return "running_header_footer"

    return None


def pre_filter_lines(
    document: ParsedDocument,
) -> tuple[list[ParsedLine], dict[str, Any]]:
    """Return candidate lines for LLM review plus a removal report."""

    if not document.lines:
        return [], {
            "excluded_line_ids": [],
            "excluded_line_count": 0,
            "kept_line_count": 0,
            "dropped_sections": [],
            "reasons": {},
        }

    running_headers = _running_header_texts(document.lines)
    kept: list[ParsedLine] = []
    excluded_line_ids: list[str] = []
    dropped_sections: list[str] = []
    reasons: Counter[str] = Counter()
    skipping_section = False

    for line in document.lines:
        if _is_heading_line(line):
            if _is_forbidden_heading(line.text):
                skipping_section = True
                dropped_sections.append(line.text.strip())
                excluded_line_ids.append(line.line_id)
                reasons["front_back_matter_section"] += 1
                continue
            skipping_section = False
            kept.append(line)
            continue

        if skipping_section:
            excluded_line_ids.append(line.line_id)
            reasons["front_back_matter_body"] += 1
            continue

        reason = _clutter_reason(line.text, running_headers)
        if reason is not None:
            excluded_line_ids.append(line.line_id)
            reasons[reason] += 1
            continue

        kept.append(line)

    return kept, {
        "excluded_line_ids": excluded_line_ids,
        "excluded_line_count": len(excluded_line_ids),
        "kept_line_count": len(kept),
        "dropped_sections": dropped_sections,
        "reasons": dict(reasons),
    }


def validate_prepared_document(document: ParsedDocument) -> dict[str, Any]:
    """Validate that no forbidden patterns remain. Raises on failure."""

    violations: Counter[str] = Counter()
    violation_line_ids: list[str] = []
    skipping_section = False
    running_headers = _running_header_texts(document.lines)

    for line in document.lines:
        if _is_heading_line(line):
            if _is_forbidden_heading(line.text):
                skipping_section = True
                violations["forbidden_section_heading"] += 1
                violation_line_ids.append(line.line_id)
                continue
            skipping_section = False
            continue

        if skipping_section:
            violations["forbidden_section_body"] += 1
            violation_line_ids.append(line.line_id)
            continue

        reason = _clutter_reason(line.text, running_headers)
        if reason is not None:
            violations[reason] += 1
            violation_line_ids.append(line.line_id)

    report = {
        "valid": not violations,
        "violations": dict(violations),
        "violation_line_ids": violation_line_ids,
    }

    if violations:
        summary = ", ".join(f"{key}={count}" for key, count in violations.items())
        raise RuntimeError(
            f"Prepare validation failed: forbidden content remains ({summary}).",
        )

    return report
