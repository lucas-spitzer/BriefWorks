from __future__ import annotations

import re
import statistics

import fitz

from app.intellex.models import ParsedDocument, ParsedLine

_HEADER_FOOTER_RE = re.compile(
    r"^(page\s+\d+|\d+\s*$|confidential|unclassified|for official use only)$",
    re.IGNORECASE,
)
_SECTION_NUMBER_RE = re.compile(r"^\d+(\.\d+)*\s+\S")
_CHAPTER_RE = re.compile(r"^(chapter|section|appendix|part)\s+[\divxlc]+", re.IGNORECASE)


def _normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _median_body_font_size(lines: list[ParsedLine]) -> float:
    sizes = [line.font_size for line in lines if line.font_size > 0]

    if not sizes:
        return 12.0

    return float(statistics.median(sizes))


def is_heading_line(text: str, font_size: float, body_median_size: float) -> bool:
    stripped = text.strip()

    if len(stripped) < 3:
        return False

    if _HEADER_FOOTER_RE.match(stripped):
        return False

    if font_size >= body_median_size * 1.15 and len(stripped) <= 200:
        return True

    if (
        len(stripped) <= 80
        and stripped.isupper()
        and any(character.isalpha() for character in stripped)
    ):
        return True

    if _SECTION_NUMBER_RE.match(stripped) and len(stripped) <= 200:
        return True

    if _CHAPTER_RE.match(stripped) and len(stripped) <= 200:
        return True

    return False


def parse_pdf(content: bytes) -> ParsedDocument:
    document = fitz.open(stream=content, filetype="pdf")
    page_count = len(document)
    lines: list[ParsedLine] = []

    try:
        for page_index, page in enumerate(document, start=1):
            page_dict = page.get_text("dict")
            line_index = 0

            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    line_text = _normalize_line("".join(span.get("text", "") for span in spans))

                    if not line_text:
                        continue

                    if _HEADER_FOOTER_RE.match(line_text):
                        continue

                    font_sizes = [
                        float(span.get("size", 0))
                        for span in spans
                        if float(span.get("size", 0)) > 0
                    ]
                    font_size = max(font_sizes) if font_sizes else 0.0
                    bbox = [float(value) for value in line.get("bbox", [])]

                    lines.append(
                        ParsedLine(
                            line_id=f"p{page_index}-l{line_index}",
                            text=line_text,
                            page=page_index,
                            font_size=font_size,
                            bbox=bbox,
                        ),
                    )
                    line_index += 1
    finally:
        document.close()

    return ParsedDocument(page_count=page_count, lines=lines)


def classify_lines(document: ParsedDocument) -> list[tuple[str, ParsedLine]]:
    body_median = _median_body_font_size(document.lines)
    classified: list[tuple[str, ParsedLine]] = []

    for line in document.lines:
        kind = "heading" if is_heading_line(line.text, line.font_size, body_median) else "paragraph"
        classified.append((kind, line))

    return classified
