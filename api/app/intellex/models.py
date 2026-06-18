from dataclasses import dataclass, field
from typing import Any, Literal

LineKind = Literal["heading", "paragraph"]


@dataclass(frozen=True)
class ParsedLine:
    text: str
    page: int
    font_size: float = 0.0
    bbox: list[float] = field(default_factory=list)
    line_id: str = ""
    kind: LineKind | None = None


@dataclass
class ParsedDocument:
    page_count: int
    lines: list[ParsedLine] = field(default_factory=list)
    parser: str = "pymupdf"
    job_id: str | None = None

    def to_parse_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "page_count": self.page_count,
            "line_count": len(self.lines),
            "parser": self.parser,
        }

        if self.job_id:
            metadata["llamaparse_job_id"] = self.job_id

        return metadata


@dataclass(frozen=True)
class ParseResult:
    document: ParsedDocument
    raw_markdown: str
