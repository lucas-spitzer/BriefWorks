import fitz

from app.intellex.pdf_parser import is_heading_line, parse_pdf


def _make_pdf(text_blocks: list[tuple[str, float]]) -> bytes:
    document = fitz.open()
    page = document.new_page()

    y_position = 72.0

    for text, font_size in text_blocks:
        page.insert_text((72, y_position), text, fontsize=font_size)
        y_position += font_size + 8

    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_parse_pdf_extracts_lines_with_page_numbers() -> None:
    pdf_bytes = _make_pdf(
        [
            ("CHAPTER 1", 18.0),
            ("Body text for the chapter.", 12.0),
        ],
    )

    parsed = parse_pdf(pdf_bytes)

    assert parsed.page_count == 1
    assert len(parsed.lines) >= 2
    assert any(line.text == "CHAPTER 1" for line in parsed.lines)
    assert any("Body text" in line.text for line in parsed.lines)
    assert all(line.page == 1 for line in parsed.lines)


def test_is_heading_line_detects_numbered_sections() -> None:
    assert is_heading_line("1.1 Purpose", 12.0, 12.0) is True
    assert is_heading_line("Regular body sentence.", 12.0, 12.0) is False
