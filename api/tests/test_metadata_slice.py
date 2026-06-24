from app.intellex.metadata_slice import build_metadata_slice, build_source_research_slices
from app.intellex.models import ParsedDocument, ParsedLine


def test_build_metadata_slice_prefers_early_pages() -> None:
    document = ParsedDocument(
        page_count=10,
        lines=[
            ParsedLine(text="MCDP 1 Warfighting", page=1, font_size=16.0),
            ParsedLine(text="United States Marine Corps", page=1, font_size=12.0),
            ParsedLine(text="Late page content", page=9, font_size=12.0),
        ],
    )

    sample = build_metadata_slice(document, max_chars=500)

    assert "MCDP 1 Warfighting" in sample
    assert "Late page content" not in sample


def test_build_source_research_slices_extracts_preface() -> None:
    document = ParsedDocument(
        page_count=20,
        lines=[
            ParsedLine(text="MCDP 1 Warfighting", page=1, kind="heading"),
            ParsedLine(text="United States Marine Corps", page=1),
            ParsedLine(text="Preface", page=2, kind="heading"),
            ParsedLine(text="This publication describes warfighting doctrine.", page=2),
            ParsedLine(text="Late page content", page=15),
        ],
    )

    slices = build_source_research_slices(document)

    assert "MCDP 1 Warfighting" in slices["cover"]
    assert "Preface" in slices["preface"]
    assert "warfighting doctrine" in slices["preface"]
    assert "Late page content" not in slices["preface"]


def test_build_source_research_slices_extracts_toc() -> None:
    document = ParsedDocument(
        page_count=20,
        lines=[
            ParsedLine(text="Report Title", page=1),
            ParsedLine(text="Table of Contents", page=3, kind="heading"),
            ParsedLine(text="Chapter 1 Overview", page=3),
            ParsedLine(text="Chapter 2 Methods", page=3),
            ParsedLine(text="Chapter 1", page=10, kind="heading"),
            ParsedLine(text="Body content", page=10),
        ],
    )

    slices = build_source_research_slices(document)

    assert "Table of Contents" in slices["toc"]
    assert "Chapter 1 Overview" in slices["toc"]
    assert "Body content" not in slices["toc"]


def test_build_source_research_slices_respects_char_budget() -> None:
    long_line = "x" * 500
    document = ParsedDocument(
        page_count=5,
        lines=[
            ParsedLine(text=long_line, page=1),
            ParsedLine(text=long_line, page=1),
            ParsedLine(text=long_line, page=1),
            ParsedLine(text=long_line, page=1),
            ParsedLine(text=long_line, page=4),
            ParsedLine(text=long_line, page=4),
        ],
    )

    slices = build_source_research_slices(document, max_chars=1_000)
    total = sum(len(value) for value in slices.values())

    assert total <= 1_000
