"""HTML-to-PDF print seam. WeasyPrint is the production adapter."""

from __future__ import annotations

from typing import Protocol

import fitz


class PdfPrinter(Protocol):
    def print_html(self, html: str) -> bytes:
        """Render a full HTML document to PDF bytes."""
        ...

    def page_count(self, pdf: bytes) -> int:
        """Return the page count of a PDF."""
        ...


class WeasyPrintPdfPrinter:
    """Print CSS HTML to PDF. Requires the weasyprint extra (Pango/Cairo)."""

    def print_html(self, html: str) -> bytes:
        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise RuntimeError(
                "weasyprint is required to print study sheets. "
                "Install it in the API environment (Pango/Cairo on the host).",
            ) from exc
        pdf = HTML(string=html, base_url=".").write_pdf()
        if not pdf:
            raise RuntimeError("Study sheet print produced an empty PDF.")
        return pdf

    def page_count(self, pdf: bytes) -> int:
        document = fitz.open(stream=pdf, filetype="pdf")
        try:
            return int(document.page_count)
        finally:
            document.close()
