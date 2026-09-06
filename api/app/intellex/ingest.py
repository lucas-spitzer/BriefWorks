from __future__ import annotations

from typing import Any

from app.intellex.chunker import build_ndr_segments
from app.intellex.llamaparse_normalizer import normalize_llamaparse_result
from app.intellex.models import ParseResult, ParsedDocument
from app.services.llamaparse_client import LlamaParseClient

PDF_MIME_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


def is_pdf_source(mime_type: str, filename: str) -> bool:
    if mime_type in PDF_MIME_TYPES:
        return True

    return filename.lower().endswith(".pdf")


def parse_source_content(
    *,
    mime_type: str,
    filename: str,
    content: bytes,
    llamaparse_client: LlamaParseClient | None = None,
) -> ParseResult:
    if not is_pdf_source(mime_type, filename):
        raise ValueError(
            f"Unsupported source type for parse stage: {mime_type or filename}. "
            "Only PDF sources are supported for parsing.",
        )

    if not content:
        raise ValueError("Source file is empty.")

    client = llamaparse_client or LlamaParseClient()
    parse_result = client.parse_pdf(filename=filename or "source.pdf", content=content)
    document = normalize_llamaparse_result(parse_result)
    return ParseResult(
        document=document,
        raw_markdown=parse_result.raw_markdown,
        api_payload=parse_result.api_payload,
        structured_pages=parse_result.structured_pages,
    )


def chunk_parsed_document(
    *,
    parsed_document: ParsedDocument,
    source_id: str,
    workspace_id: str,
) -> list[dict[str, Any]]:
    """Legacy line-based chunker, retained for any non-structured callers/tests.

    The structure-based pipeline chunks from the Book model instead; see
    app.intellex.structuring.chunk.build_segments_and_chapters.
    """
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
