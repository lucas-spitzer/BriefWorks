"""Classify parsed headings for prepare, chunk, and chapter segmentation."""

from __future__ import annotations

import re

_CHAPTER_BOUNDARY_RE = re.compile(
    r"^(chapter|part|unit|lesson)\s+[\divxlc]+\s*\.?\s*$",
    re.IGNORECASE,
)
_CHAPTER_WITH_TITLE_RE = re.compile(
    r"^(chapter|part|unit|lesson)\s+[\divxlc]+\s*[:.\-—–]\s*\S",
    re.IGNORECASE,
)
_SECTION_BOUNDARY_RE = re.compile(
    r"^(section|annex|appendix)\s+[\divxlc]+",
    re.IGNORECASE,
)


_TOC_CHAPTER_LISTING_RE = re.compile(
    r"^(chapter|part|unit|lesson)\s+[\divxlc]+\s*\.\s*$",
    re.IGNORECASE,
)


def is_toc_chapter_listing_heading(text: str) -> bool:
    """TOC lines like 'Chapter 1.' with only a trailing period."""
    return bool(_TOC_CHAPTER_LISTING_RE.match(text.strip()))


def is_toc_outline_line(text: str) -> bool:
    """Dash-chained topic lists from table-of-contents pages."""
    stripped = text.strip()

    if not stripped or len(stripped) > 200:
        return False

    dash_parts = re.split(r"\s*[—–\-]\s*", stripped)

    if len(dash_parts) < 2:
        return False

    if any(len(part) > 60 for part in dash_parts):
        return False

    if any(". " in part for part in dash_parts):
        return False

    if stripped.endswith(".") and len(dash_parts) == 2:
        return False

    return all(len(part) <= 45 for part in dash_parts)


_RUNNING_HEADER_CORRUPTION_RE = re.compile(r"^Tm\s+", re.IGNORECASE)


def normalize_doctrinal_heading(text: str) -> str:
    return _RUNNING_HEADER_CORRUPTION_RE.sub("THE ", text.strip())


def is_doctrinal_subsection_heading(text: str) -> bool:
    """ALL-CAPS doctrinal subsection titles such as 'THE EVOLUTION OF WAR'."""
    stripped = normalize_doctrinal_heading(text)

    if not stripped or len(stripped) > 120:
        return False

    if is_chapter_boundary_heading(stripped) or is_section_boundary_heading(stripped):
        return False

    letters = [character for character in stripped if character.isalpha()]

    if not letters:
        return False

    if stripped.isupper():
        return True

    upper_count = sum(1 for character in letters if character.isupper())
    return upper_count / len(letters) >= 0.85 and len(stripped.split()) <= 12


def is_chapter_boundary_heading(text: str) -> bool:
    """True when a heading starts a new top-level chapter/part."""
    stripped = text.strip()

    if not stripped:
        return False

    if is_toc_chapter_listing_heading(stripped):
        return False

    if _CHAPTER_BOUNDARY_RE.match(stripped):
        return True

    if _CHAPTER_WITH_TITLE_RE.match(stripped):
        return True

    return False


def is_section_boundary_heading(text: str) -> bool:
    """True for section/annex headings that stay nested under a chapter."""
    stripped = text.strip()

    if not stripped:
        return False

    return bool(_SECTION_BOUNDARY_RE.match(stripped))


_CHAPTER_NUMBER_RE = re.compile(r"^chapter\s+([\divxlc]+)", re.IGNORECASE)

_ROMAN_NUMERALS = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
}


def parse_chapter_boundary_number(text: str) -> int | None:
    """Return the chapter number for headings like 'Chapter 2' or 'Chapter 2: Title'."""
    stripped = text.strip()

    if not is_chapter_boundary_heading(stripped):
        return None

    match = _CHAPTER_NUMBER_RE.match(stripped)

    if not match:
        return None

    token = match.group(1).lower()

    if token.isdigit():
        return int(token)

    return _ROMAN_NUMERALS.get(token)
