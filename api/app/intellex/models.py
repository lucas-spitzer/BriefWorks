from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParsedLine:
    text: str
    page: int
    font_size: float
    bbox: list[float] = field(default_factory=list)


@dataclass
class ParsedDocument:
    page_count: int
    lines: list[ParsedLine] = field(default_factory=list)
    parser: str = "pymupdf"

    def to_parse_metadata(self) -> dict[str, Any]:
        return {
            "page_count": self.page_count,
            "line_count": len(self.lines),
            "parser": self.parser,
        }
