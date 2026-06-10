from __future__ import annotations

from typing import Any

from app.intellex.chunker import build_ndr_segments
from app.intellex.models import ParsedDocument
from app.intellex.pdf_parser import parse_pdf

PDF_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


def is_pdf_source(mime_type: str, filename: str) -> bool:
    if mime_type in PDF_MIME_TYPES:
        return True

    return filename.lower().endswith(".pdf")


def parse_source_content(*, mime_type: str, filename: str, content: bytes) -> ParsedDocument:
    if not is_pdf_source(mime_type, filename):
        raise ValueError(
            f"Unsupported source type for parse step: {mime_type or filename}. "
            "Phase B supports PDF only.",
        )

    if not content:
        raise ValueError("Source file is empty.")

    return parse_pdf(content)


def chunk_parsed_document(
    *,
    parsed_document: ParsedDocument,
    source_id: str,
    workspace_id: str,
) -> list[dict[str, Any]]:
    segments = build_ndr_segments(parsed_document)

    return [
        {
            "id": segment["id"],
            "source_id": source_id,
            "workspace_id": workspace_id,
            "sequence_index": segment["sequence_index"],
            "kind": segment["kind"],
            "text": segment["text"],
            "locator": segment["locator"],
        }
        for segment in segments
    ]
