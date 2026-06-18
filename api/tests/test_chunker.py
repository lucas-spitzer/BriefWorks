from app.intellex.chunker import build_ndr_segments
from app.intellex.models import ParsedDocument, ParsedLine


def test_build_ndr_segments_respects_markdown_line_kind() -> None:
    document = ParsedDocument(
        page_count=1,
        lines=[
            ParsedLine(text="Chapter 1", page=1, kind="heading"),
            ParsedLine(text="First sentence.", page=1, kind="paragraph"),
            ParsedLine(text="Second sentence.", page=1, kind="paragraph"),
        ],
        parser="llamaparse",
    )

    segments = build_ndr_segments(document)

    assert len(segments) == 2
    assert segments[0]["kind"] == "heading"
    assert segments[1]["text"] == "First sentence. Second sentence."


def test_build_ndr_segments_merges_paragraph_lines_and_keeps_headings() -> None:
    document = ParsedDocument(
        page_count=2,
        lines=[
            ParsedLine(text="CHAPTER 1", page=1, font_size=18.0),
            ParsedLine(text="First sentence.", page=1, font_size=12.0),
            ParsedLine(text="Second sentence.", page=1, font_size=12.0),
            ParsedLine(text="1.1 Purpose", page=2, font_size=14.0),
            ParsedLine(text="Doctrine explains intent.", page=2, font_size=12.0),
        ],
    )

    segments = build_ndr_segments(document)

    assert len(segments) == 4
    assert segments[0]["kind"] == "heading"
    assert segments[0]["text"] == "CHAPTER 1"
    assert segments[1]["kind"] == "paragraph"
    assert segments[1]["text"] == "First sentence. Second sentence."
    assert segments[2]["kind"] == "heading"
    assert segments[2]["text"] == "1.1 Purpose"
    assert segments[3]["kind"] == "paragraph"
    assert segments[3]["locator"]["page"] == 2
