"""Stage: VALIDATE (pdf-structure-validation).

The earlier stages decide structure from the LlamaParse output alone; this stage
independently checks that decision against the source PDF so a parsing quirk
can't silently corrupt the book. It runs fully automatically and RAISES on
failure so a bad run stops loudly instead of shipping a broken EPUB.

Checks (by re-reading the PDF text layer with PyMuPDF):
  1. Every chapter/section title appears on or near its recorded page.
  2. No known front/back-matter label (FOREWORD, NOTES, GLOSSARY, INDEX...)
     survives as a chapter or section.
  3. The body carries real text.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import fitz  # PyMuPDF

from app.intellex.structuring.models import Book

_FRONT_BACK_LABELS = re.compile(
    r"^(table of contents|contents|foreword|preface|dedication|acknowledge?ments?|"
    r"notes?|endnotes?|glossary|bibliography|references?|index|appendix\b|epilogue|"
    r"afterword|about the author)",
    re.IGNORECASE,
)

# LlamaParse page numbers and the PDF's own page indices can drift by a page.
PAGE_SLACK = 2


class StructureValidationError(RuntimeError):
    """Raised when the structured book disagrees with the source PDF."""


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _pdf_pages(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [_norm(page.get_text("text")) for page in doc]
    finally:
        doc.close()


def _near(title: str, page: int | None, pages: list[str]) -> bool:
    needle = _norm(title)
    if not needle:
        return True
    lo = max(0, (page or 1) - 1 - PAGE_SLACK)
    hi = min(len(pages), (page or 1) - 1 + PAGE_SLACK + 1)
    return any(needle in pages[i] for i in range(lo, hi))


def _anywhere(title: str, pages: list[str]) -> bool:
    needle = _norm(title)
    return any(needle in p for p in pages) if needle else True


def validate_against_pdf(book: Book, pdf_bytes: bytes) -> dict[str, Any]:
    """Return a report dict; raise StructureValidationError on hard failure."""
    pages = _pdf_pages(pdf_bytes)
    errors: list[str] = []
    warnings: list[str] = []

    if not book.chapters:
        raise StructureValidationError("Structured book has no chapters.")

    for c in book.chapters:
        if _FRONT_BACK_LABELS.match(c.title.strip()):
            errors.append(f"Front/back-matter heading leaked as a CHAPTER: {c.title!r}")
        if not _near(c.title, c.page, pages):
            (warnings if _anywhere(c.title, pages) else errors).append(
                f"Chapter {c.title!r} not found near p{c.page}"
                + ("" if _anywhere(c.title, pages) else " in the PDF at all")
            )
        for s in c.sections:
            if _FRONT_BACK_LABELS.match(s.title.strip()):
                errors.append(f"Front/back-matter heading leaked as a SECTION: {s.title!r}")
            if not _near(s.title, s.page, pages):
                (warnings if _anywhere(s.title, pages) else errors).append(
                    f"Section {s.title!r} not found near p{s.page}"
                    + ("" if _anywhere(s.title, pages) else " in the PDF at all")
                )

    n_headings = sum(1 + len(c.sections) for c in book.chapters)
    body = book.body_paragraph_count()
    if body < max(3, n_headings):
        errors.append(f"Body looks too thin ({body} paragraphs for {n_headings} headings).")

    report = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked": {
            "chapters": len(book.chapters),
            "sections": sum(len(c.sections) for c in book.chapters),
            "body_paragraphs": body,
            "pdf_pages": len(pages),
        },
    }
    if errors:
        raise StructureValidationError(
            "Structure validation failed: " + "; ".join(errors)
        )
    return report
