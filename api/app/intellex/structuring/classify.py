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
      the chapter intro before the first section). Text split by a PDF page
      boundary or an omitted visual is rejoined conservatively. Footnote/citation
      superscript markers are stripped by default because they point into a
      removed notes section and would otherwise dangle. Chapter epigraphs stay
      as separate paragraphs (quote vs attribution) so EPUB spacing is preserved.

Non-text, non-heading elements (lists, code/diagrams, images) are not one of the
three KEEP types and are dropped, with counts reported. Standalone captions for
those omitted visuals are dropped as well; inline prose references are retained.
Omitted visuals and their captions are transparent to paragraph continuity so a
sentence interrupted by a figure can be rejoined.
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
_VISUAL_CAPTION_RE = re.compile(
    r"^\s*(?:figure|fig\.?|table|tbl\.?|plate|exhibit|chart|diagram|"
    r"illustration|map|photo)\s+(?:\d+|[ivxlcdm]+)\s*(?:[.:\-–—]|$)",
    re.IGNORECASE,
)
_PARAGRAPH_END_RE = re.compile(r"""[.!?]["'”’)\]]*\s*$""")
_TRAILING_EMPHASIS_RE = re.compile(r"[*_]+$")
_LEADING_EMPHASIS_RE = re.compile(r"^[*_]+")
_ATTRIBUTION_LINE_RE = re.compile(r"^\s*[—–\-]\s*\S")
_ATTRIBUTION_SPLIT_RE = re.compile(r"\n+(?=\s*[*_]*[—–\-]\s*\S)")
_MAX_CAPTION_LENGTH = 200
_OMITTED_VISUAL_TYPES = frozenset(
    {"image", "figure", "diagram", "chart", "illustration", "photo", "code"}
)
_VISUAL_LAYOUT_LABELS = frozenset(
    {"image", "figure", "diagram", "chart", "illustration", "photo", "caption", "table"}
)
_NON_SECTION_LAYOUT_LABELS = _VISUAL_LAYOUT_LABELS | {"header", "footer"}
_FRAGMENTED_VISUAL_MAX_CONFIDENCE = 0.5
_FRAGMENTED_VISUAL_MIN_BOXES = 4


def strip_footnote_markers(md: str) -> str:
    out = _SUP_TAG_RE.sub("", md)
    out = _UNICODE_SUP_RE.sub("", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    return out.strip()


def is_standalone_visual_caption(text: str) -> bool:
    """Return whether a short text item is a label for an omitted visual.

    Requiring the identifier at the start and punctuation after its number
    deliberately preserves prose such as "As shown in Figure 1..." and
    "Figure 1 shows...".
    """
    stripped = text.strip()
    return len(stripped) <= _MAX_CAPTION_LENGTH and bool(_VISUAL_CAPTION_RE.match(stripped))


def _looks_like_fragmented_visual_text(element: Element) -> bool:
    """Detect OCR assembled from many low-confidence labels inside a visual."""
    return (
        element.type == "text"
        and set(element.layout_labels) == {"text"}
        and element.max_layout_confidence is not None
        and element.max_layout_confidence <= _FRAGMENTED_VISUAL_MAX_CONFIDENCE
        and element.layout_fragment_count >= _FRAGMENTED_VISUAL_MIN_BOXES
    )


def _fragmented_visual_pages(elements: list[Element]) -> set[int | None]:
    """Pages where a generic heading fronts fragmented map/diagram OCR."""
    ambiguous_heading_pages = {
        element.page
        for element in elements
        if element.type == "heading" and set(element.layout_labels) == {"text"}
    }
    return {
        element.page
        for element in elements
        if element.page in ambiguous_heading_pages
        and _looks_like_fragmented_visual_text(element)
    }


def _explicit_visual_pages(elements: list[Element]) -> set[int | None]:
    return {
        element.page
        for element in elements
        if element.type in _OMITTED_VISUAL_TYPES
        or set(element.layout_labels) & _VISUAL_LAYOUT_LABELS
    }


def _is_visual_description(
    element: Element,
    *,
    fragmented_visual_pages: set[int | None],
    explicit_visual_pages: set[int | None],
) -> bool:
    labels = set(element.layout_labels)
    visual_labels = labels & _VISUAL_LAYOUT_LABELS
    nonvisual_labels = labels - _VISUAL_LAYOUT_LABELS
    if visual_labels and not nonvisual_labels:
        return True
    if "image" in visual_labels and "paragraph_title" in nonvisual_labels:
        return True
    if (
        visual_labels
        and element.min_layout_confidence is not None
        and element.min_layout_confidence <= _FRAGMENTED_VISUAL_MAX_CONFIDENCE
    ):
        return True
    if (
        not labels
        and element.page in explicit_visual_pages
        and len(element.text.split()) <= 8
        and not _paragraph_looks_complete(element.text)
    ):
        return True
    return (
        element.page in fragmented_visual_pages
        and _looks_like_fragmented_visual_text(element)
    )


def _is_visual_heading(
    element: Element,
    *,
    fragmented_visual_pages: set[int | None],
) -> bool:
    """Return whether parser provenance contradicts a section heading."""
    if is_standalone_visual_caption(element.text):
        return True

    labels = set(element.layout_labels)
    if not labels or "paragraph_title" in labels:
        return False
    if labels & _NON_SECTION_LAYOUT_LABELS:
        return True
    return labels == {"text"} and element.page in fragmented_visual_pages


def _paragraph_looks_complete(md: str) -> bool:
    """True when md ends a sentence after ignoring trailing markdown emphasis."""
    stripped = _TRAILING_EMPHASIS_RE.sub("", md.strip()).rstrip()
    return bool(_PARAGRAPH_END_RE.search(stripped))


def _is_attribution_line(text: str) -> bool:
    stripped = _LEADING_EMPHASIS_RE.sub("", text.strip()).lstrip()
    return bool(_ATTRIBUTION_LINE_RE.match(stripped))


def _split_epigraph_markdown(md: str) -> list[str]:
    """Split quote + attribution that LlamaParse packed into one text item."""
    parts = [part.strip() for part in _ATTRIBUTION_SPLIT_RE.split(md) if part.strip()]
    return parts if len(parts) > 1 else [md]


def _continues_paragraph(previous: Element, current: Element) -> bool:
    """Detect one paragraph split by a page break and/or omitted visual."""
    if not isinstance(previous.page, int) or not isinstance(current.page, int):
        return False
    if current.page not in (previous.page, previous.page + 1):
        return False
    previous_md = previous.md or previous.text
    current_md = (current.md or current.text).strip()
    # Epigraph attributions are their own paragraphs; never glue them to
    # neighboring quotes or body text.
    if _is_attribution_line(previous_md) or _is_attribution_line(previous.text):
        return False
    if _is_attribution_line(current_md) or _is_attribution_line(current.text):
        return False
    return not _paragraph_looks_complete(previous_md)


def _join_markdown(left: str, right: str) -> str:
    return f"{left.rstrip()} {right.lstrip()}"


def _chapter_title(marker_text: str, next_heading_text: str | None) -> tuple[str, bool]:
    """Return (title, consumed_next_heading)."""
    m = _EMBEDDED_TITLE_RE.match(marker_text)
    if m and m.group(1).strip():
        num = _CHAPTER_NUM_RE.match(marker_text).group(1).strip()
        return f"{num} {m.group(1).strip()}", False
    if next_heading_text:
        return f"{marker_text.strip()} {next_heading_text.strip()}", True
    return marker_text.strip(), False


def _append_paragraph(
    *,
    chapter: Chapter,
    section: Section | None,
    md: str,
    page: int | None,
) -> Paragraph:
    para = Paragraph(md=md, page=page)
    if section is None:
        chapter.intro.append(para)
    else:
        section.body.append(para)
    return para


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
    previous_body_element: Element | None = None
    previous_paragraph: Paragraph | None = None
    n = len(elements)
    fragmented_visual_pages = _fragmented_visual_pages(elements)
    explicit_visual_pages = _explicit_visual_pages(elements)

    for idx, el in enumerate(elements):
        if el.type == "heading":
            if consume_next_heading:
                previous_body_element = None
                previous_paragraph = None
                consume_next_heading = False  # already merged into the chapter title
                continue

            if is_chapter_marker(el.text, chapter_re):
                next_element = elements[idx + 1] if idx + 1 < n else None
                next_text = None
                if (
                    next_element is not None
                    and next_element.type == "heading"
                    and not _is_visual_heading(
                        next_element,
                        fragmented_visual_pages=fragmented_visual_pages,
                    )
                ):
                    next_text = next_element.text
                title, consumed = _chapter_title(el.text, next_text)
                consume_next_heading = consumed
                previous_body_element = None
                previous_paragraph = None
                current_chapter = Chapter(title=title, page=el.page)
                current_section = None
                book.chapters.append(current_chapter)
            else:
                if _is_visual_heading(
                    el,
                    fragmented_visual_pages=fragmented_visual_pages,
                ):
                    book.dropped_nontext["visual_heading"] = (
                        book.dropped_nontext.get("visual_heading", 0) + 1
                    )
                    # Like an omitted caption, a visual heading does not break
                    # the surrounding authored reading flow.
                    continue
                previous_body_element = None
                previous_paragraph = None
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
                previous_body_element = None
                previous_paragraph = None
                continue
            if _is_visual_description(
                el,
                fragmented_visual_pages=fragmented_visual_pages,
                explicit_visual_pages=explicit_visual_pages,
            ):
                book.dropped_nontext["visual_description"] = (
                    book.dropped_nontext.get("visual_description", 0) + 1
                )
                # Generated descriptions of omitted visuals are not source
                # prose and remain transparent to reading order.
                continue
            if is_standalone_visual_caption(el.text or md):
                book.dropped_nontext["caption"] = book.dropped_nontext.get("caption", 0) + 1
                # Captions for omitted visuals are transparent to continuity.
                continue
            if (
                previous_body_element is not None
                and previous_paragraph is not None
                and _continues_paragraph(previous_body_element, el)
            ):
                previous_paragraph.md = _join_markdown(previous_paragraph.md, md)
                previous_body_element = el
                continue

            parts = _split_epigraph_markdown(md)
            last_para: Paragraph | None = None
            for part in parts:
                last_para = _append_paragraph(
                    chapter=current_chapter,
                    section=current_section,
                    md=part,
                    page=el.page,
                )
            previous_body_element = el
            previous_paragraph = last_para

        else:  # list / code / image / etc -- not a KEEP type
            book.dropped_nontext[el.type] = book.dropped_nontext.get(el.type, 0) + 1
            if el.type not in _OMITTED_VISUAL_TYPES:
                previous_body_element = None
                previous_paragraph = None

    return book
