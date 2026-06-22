"""Stage: STRUCTURE (document-structure-classify).

Turn the trimmed element stream into a clean chapter/section/body Book. This is
where the three KEEP rules are applied and where chapter grouping happens -- so
it replaces the old deconstruct-document step as well as the structural half of
prepare-document.

  H1 chapters: a heading matching the chapter pattern. A bare "Chapter N" is
      merged with the following heading into "Chapter N <Title>"; a marker that
      already embeds a title is used as-is.
  H2 sections: EVERY other in-body heading, regardless of LlamaParse `level`
      (which is too noisy to separate chapters from sections).
  Body: every `text` element in reading order, attached to its section (or to
      the chapter intro before the first section). Footnote/citation superscript
      markers are stripped by default because they point into a removed notes
      section and would otherwise dangle.

Non-text, non-heading elements (lists, code/diagrams, images) are not one of the
three KEEP types and are dropped, with counts reported.
"""
from __future__ import annotations

import re

from app.intellex.structuring.boundaries import is_chapter_marker
from app.intellex.structuring.models import Book, Chapter, Element, Paragraph, Section

DEFAULT_CHAPTER_RE = r"^\s*chapter\s+\d+\s*$"
_EMBEDDED_TITLE_RE = re.compile(r"^\s*chapter\s+\d+\s*[.:\-]\s*(.+)$", re.IGNORECASE)
_CHAPTER_NUM_RE = re.compile(r"^\s*(chapter\s+\d+)", re.IGNORECASE)

_SUP_TAG_RE = re.compile(r"<sup>.*?</sup>", re.IGNORECASE | re.DOTALL)
_UNICODE_SUP_RE = re.compile(r"[\u00b2\u00b3\u00b9\u2070\u2074-\u2079]+")


def strip_footnote_markers(md: str) -> str:
    out = _SUP_TAG_RE.sub("", md)
    out = _UNICODE_SUP_RE.sub("", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    return out.strip()


def _chapter_title(marker_text: str, next_heading_text: str | None) -> tuple[str, bool]:
    """Return (title, consumed_next_heading)."""
    m = _EMBEDDED_TITLE_RE.match(marker_text)
    if m and m.group(1).strip():
        num = _CHAPTER_NUM_RE.match(marker_text).group(1).strip()
        return f"{num} {m.group(1).strip()}", False
    if next_heading_text:
        return f"{marker_text.strip()} {next_heading_text.strip()}", True
    return marker_text.strip(), False


def classify(
    elements: list[Element],
    *,
    chapter_re: str = DEFAULT_CHAPTER_RE,
    strip_markers: bool = True,
) -> Book:
    book = Book()
    current_chapter: Chapter | None = None
    current_section: Section | None = None
    consume_next_heading = False
    n = len(elements)

    for idx, el in enumerate(elements):
        if el.type == "heading":
            if consume_next_heading:
                consume_next_heading = False  # already merged into the chapter title
                continue

            if is_chapter_marker(el.text, chapter_re):
                next_text = (
                    elements[idx + 1].text
                    if idx + 1 < n and elements[idx + 1].type == "heading"
                    else None
                )
                title, consumed = _chapter_title(el.text, next_text)
                consume_next_heading = consumed
                current_chapter = Chapter(title=title, page=el.page)
                current_section = None
                book.chapters.append(current_chapter)
            else:
                if current_chapter is None:  # safety net (shouldn't happen post-trim)
                    current_chapter = Chapter(title="(untitled)", page=el.page)
                    book.chapters.append(current_chapter)
                current_section = Section(title=el.text.strip(), page=el.page)
                current_chapter.sections.append(current_section)

        elif el.type == "text":
            md = el.md or el.text
            if strip_markers:
                md = strip_footnote_markers(md)
            if not md.strip() or current_chapter is None:
                continue
            para = Paragraph(md=md, page=el.page)
            if current_section is None:
                current_chapter.intro.append(para)
            else:
                current_section.body.append(para)

        else:  # list / code / image / etc -- not a KEEP type
            book.dropped_nontext[el.type] = book.dropped_nontext.get(el.type, 0) + 1

    return book
