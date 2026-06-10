from __future__ import annotations

from app.intellex.models import ParsedDocument


def sample_text_for_research(
    document: ParsedDocument,
    *,
    max_chars: int = 12_000,
) -> str:
    """Prefer early pages where title, authority, and publication data usually appear."""
    if not document.lines:
        return ""

    chunks: list[str] = []
    total_chars = 0
    max_pages = 5

    for line in document.lines:
        if line.page > max_pages:
            continue

        if total_chars >= max_chars:
            break

        chunks.append(line.text)
        total_chars += len(line.text) + 1

    return "\n".join(chunks).strip()
