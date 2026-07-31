from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# LlamaParse item types that are page furniture, not content.
FURNITURE_TYPES = ("header", "footer")


@dataclass(frozen=True)
class Element:
    """One normalized content item in document reading order.

    `level` is LlamaParse's heading depth. It is intentionally NOT trusted to
    distinguish chapters from sections downstream -- in real documents the same
    kind of section heading is emitted as L1 in one place and L2 in another, so
    chapter-vs-section is decided by the chapter pattern, not depth.
    `md` keeps the original markdown so inline emphasis survives to the EPUB.
    The compact layout fields preserve LlamaParse's bbox provenance without
    carrying the full coordinate payload through every stage. They let
    classification distinguish authored prose/headings from OCR summaries of
    maps and diagrams. Empty/default values keep legacy fixtures compatible.
    """

    index: int
    page: int | None
    type: str
    level: int | None
    text: str
    md: str
    layout_labels: tuple[str, ...] = ()
    min_layout_confidence: float | None = None
    max_layout_confidence: float | None = None
    layout_fragment_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "page": self.page,
            "type": self.type,
            "level": self.level,
            "text": self.text,
            "md": self.md,
            "layout_labels": list(self.layout_labels),
            "min_layout_confidence": self.min_layout_confidence,
            "max_layout_confidence": self.max_layout_confidence,
            "layout_fragment_count": self.layout_fragment_count,
        }


@dataclass
class Paragraph:
    md: str
    page: int | None


@dataclass
class Section:
    title: str
    page: int | None
    body: list[Paragraph] = field(default_factory=list)


@dataclass
class Chapter:
    title: str
    page: int | None
    intro: list[Paragraph] = field(default_factory=list)  # body before the first section
    sections: list[Section] = field(default_factory=list)


@dataclass
class Book:
    chapters: list[Chapter] = field(default_factory=list)
    dropped_nontext: dict[str, int] = field(default_factory=dict)

    def body_paragraph_count(self) -> int:
        return sum(
            len(c.intro) + sum(len(s.body) for s in c.sections)
            for c in self.chapters
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chapters": [
                {
                    "title": c.title,
                    "page": c.page,
                    "intro": [{"md": p.md, "page": p.page} for p in c.intro],
                    "sections": [
                        {
                            "title": s.title,
                            "page": s.page,
                            "body": [{"md": p.md, "page": p.page} for p in s.body],
                        }
                        for s in c.sections
                    ],
                }
                for c in self.chapters
            ],
            "dropped_nontext": self.dropped_nontext,
        }


def book_from_dict(data: dict[str, Any]) -> Book:
    """Rebuild a Book from its to_dict() form (used to reload persisted book.json)."""
    book = Book(dropped_nontext=data.get("dropped_nontext", {}))
    for c in data.get("chapters", []):
        chapter = Chapter(title=c["title"], page=c.get("page"))
        chapter.intro = [Paragraph(md=p["md"], page=p.get("page")) for p in c.get("intro", [])]
        for s in c.get("sections", []):
            chapter.sections.append(
                Section(
                    title=s["title"],
                    page=s.get("page"),
                    body=[Paragraph(md=p["md"], page=p.get("page")) for p in s.get("body", [])],
                )
            )
        book.chapters.append(chapter)
    return book
