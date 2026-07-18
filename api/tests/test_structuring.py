import fitz
import pytest

from app.intellex.structuring.boundaries import auto_boundaries, trim
from app.intellex.structuring.chunk import build_segments_and_chapters
from app.intellex.structuring.classify import classify
from app.intellex.structuring.models import Element, book_from_dict
from app.intellex.structuring.normalize import normalize_structured_pages
from app.intellex.structuring.validate import StructureValidationError, validate_against_pdf
from app.mathesys.structured_epub import book_to_epub_chapters


def _item(itype, md, *, value=None, level=None):
    item = {"type": itype, "md": md}
    if value is not None:
        item["value"] = value
    if level is not None:
        item["level"] = level
    return item


def _page(page_number, items):
    return {"page_number": page_number, "items": items}


def _doc_pages():
    """A miniature document exercising every rule the stages must enforce."""
    return [
        _page(1, [
            _item("header", "MCDP 1"),
            _item("heading", "# Warfighting", value="Warfighting", level=1),
            _item("text", "Front matter title page.", value="Front matter title page."),
            _item("footer", "i"),
        ]),
        _page(2, [
            _item("header", "MCDP 1"),
            _item("heading", "# FOREWORD", value="FOREWORD", level=1),
            _item("text", "Front matter foreword body.", value="Front matter foreword body."),
        ]),
        _page(3, [
            _item("heading", "# Chapter 1", value="Chapter 1", level=1),       # bare marker
            _item("heading", "# The Nature of War", value="The Nature of War", level=1),  # title (merged)
            _item("text", '*"An epigraph."*<sup>1</sup>', value='"An epigraph."'),   # footnote marker
            _item("heading", "# WAR DEFINED", value="WAR DEFINED", level=1),   # section as L1
            _item("text", "War is a clash of wills.<sup>2</sup>", value="War is a clash of wills."),
            _item("code", "graph TD; A-->B", value="graph TD; A-->B"),         # figure -> dropped
            _item("heading", "## FRICTION", value="FRICTION", level=2),        # section as L2
            _item("text", "Friction makes the simple difficult.", value="Friction makes the simple difficult."),
        ]),
        _page(4, [
            _item("heading", "# Chapter 2", value="Chapter 2", level=1),
            _item("heading", "# The Theory of War", value="The Theory of War", level=1),
            _item("text", "Theory frames practice.", value="Theory frames practice."),
            _item("heading", "## CONCLUSION", value="CONCLUSION", level=2),
            _item("text", "War is an extension of policy.", value="War is an extension of policy."),
        ]),
        _page(5, [
            # Back matter: chapter titles reappear as endnote dividers.
            _item("heading", "# The Nature of War", value="The Nature of War", level=1),
            _item("list", "1. A note.\n2. Another note.", value=None),
            _item("text", "Endnote text that must be excluded.", value="Endnote text that must be excluded."),
        ]),
    ]


def _build_book():
    elements, _ = normalize_structured_pages(_doc_pages())
    start, end, _ = auto_boundaries(elements)
    return elements, classify(trim(elements, start_index=start, end_index=end))


def test_normalize_drops_headers_and_footers_and_indexes_in_order() -> None:
    elements, dropped = normalize_structured_pages(_doc_pages())

    assert dropped == {"header": 2, "footer": 1}
    assert all(e.type != "header" and e.type != "footer" for e in elements)
    # Indices are sequential reading order; page numbers are preserved.
    assert [e.index for e in elements] == list(range(len(elements)))
    assert elements[0].text == "Warfighting" and elements[0].page == 1


def test_auto_boundaries_detects_first_chapter_and_repeated_title_back_matter() -> None:
    elements, _ = normalize_structured_pages(_doc_pages())
    start, end, reasons = auto_boundaries(elements)

    start_el = next(e for e in elements if e.index == start)
    end_el = next(e for e in elements if e.index == end)
    assert start_el.text == "Chapter 1"            # skips title page + FOREWORD
    assert end_el.text == "The Nature of War" and end_el.page == 5  # endnotes divider
    assert "repeated chapter title" in reasons["end"]


def test_classify_merges_titles_ignores_level_strips_footnotes_drops_figures() -> None:
    _, book = _build_book()

    assert [c.title for c in book.chapters] == [
        "Chapter 1 The Nature of War",
        "Chapter 2 The Theory of War",
    ]
    # Sections come from headings regardless of L1/L2.
    assert [s.title for s in book.chapters[0].sections] == ["WAR DEFINED", "FRICTION"]
    # The Mermaid code block is dropped; the list (back matter) was trimmed away.
    assert book.dropped_nontext == {"code": 1}
    # Footnote markers are stripped from body and epigraph.
    assert "<sup>" not in book.chapters[0].intro[0].md
    war_defined_body = book.chapters[0].sections[0].body[0].md
    assert war_defined_body == "War is a clash of wills."
    # Back matter excluded entirely.
    all_body = " ".join(
        p.md for c in book.chapters for s in c.sections for p in s.body
    )
    assert "must be excluded" not in all_body


def test_chunk_builds_one_chapter_row_per_chapter_with_heading_first() -> None:
    _, book = _build_book()
    segments, chapters = build_segments_and_chapters(book, source_id="src-1", workspace_id="ws-1")

    assert len(chapters) == 2
    assert chapters[0]["level"] == 1
    assert chapters[0]["title"] == "Chapter 1 The Nature of War"
    # First segment of a chapter is its title heading.
    first_segment_id = chapters[0]["segment_ids"][0]
    first_segment = next(s for s in segments if s["id"] == first_segment_id)
    assert first_segment["kind"] == "heading"
    # Headings = 2 chapter titles + 3 section titles; rest are paragraphs.
    assert sum(1 for s in segments if s["kind"] == "heading") == 5
    # Segment text is plain (markdown emphasis flattened).
    assert all("*" not in s["text"] for s in segments)
    # Sections capture each level-2 heading plus its body segments.
    sections = chapters[0]["sections"]
    assert [s["title"] for s in sections] == ["WAR DEFINED", "FRICTION"]
    assert sections[0]["level"] == 2
    assert sections[0]["heading_segment_id"] == sections[0]["segment_ids"][0]
    assert all(sid in chapters[0]["segment_ids"] for sid in sections[0]["segment_ids"])


def test_epub_render_emits_three_types_and_preserves_emphasis() -> None:
    _, book = _build_book()
    chapters = book_to_epub_chapters(book)

    body = chapters[0]["xhtml_body"]
    assert body.startswith("<h1>Chapter 1 The Nature of War</h1>")
    assert "<h2>WAR DEFINED</h2>" in body
    assert "<p>War is a clash of wills.</p>" in body
    assert "<em>" in body  # epigraph italics preserved


def test_book_round_trips_through_dict() -> None:
    _, book = _build_book()
    rebuilt = book_from_dict(book.to_dict())

    assert [c.title for c in rebuilt.chapters] == [c.title for c in book.chapters]
    assert rebuilt.body_paragraph_count() == book.body_paragraph_count()


def _pdf_with_pages(page_texts: list[str]) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    data = doc.tobytes()
    doc.close()
    return data


def test_validate_passes_when_titles_present_in_pdf() -> None:
    _, book = _build_book()
    pdf = _pdf_with_pages([
        "Chapter 1 The Nature of War WAR DEFINED FRICTION",
        "Chapter 2 The Theory of War CONCLUSION",
    ])
    # Page attribution in the synthetic book (pages 3-4) won't line up with the
    # 2-page PDF, but the titles are present, so validate should pass with warnings.
    report = validate_against_pdf(book, pdf)
    assert report["valid"] is True


def test_validate_raises_when_front_matter_leaks() -> None:
    _, book = _build_book()
    book.chapters[0].title = "FOREWORD"  # simulate a missed boundary
    pdf = _pdf_with_pages(["FOREWORD", "Chapter 2 The Theory of War"])

    with pytest.raises(StructureValidationError, match="Front/back-matter heading leaked"):
        validate_against_pdf(book, pdf)
