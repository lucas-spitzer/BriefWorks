from __future__ import annotations

from app.intellex.models import ParsedDocument


def build_metadata_slice(
    document: ParsedDocument,
    *,
    max_chars: int = 12_000,
    max_pages: int = 5,
) -> str:
    """Return early-page text for bibliographic metadata extraction."""
    if not document.lines:
        return ""

    chunks: list[str] = []
    total_chars = 0

    for line in document.lines:
        if line.page > max_pages:
            continue

        if total_chars >= max_chars:
            break

        chunks.append(line.text)
        total_chars += len(line.text) + 1

    return "\n".join(chunks).strip()
