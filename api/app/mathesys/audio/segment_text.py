from __future__ import annotations

from typing import Any


def segments_to_extracted_text(segments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []

    for segment in segments:
        text = str(segment.get("text") or "").strip()

        if not text:
            continue

        kind = str(segment.get("kind") or "paragraph")

        if kind == "heading":
            blocks.append(f"# {text}")
        else:
            blocks.append(text)

    return "\n\n".join(blocks)


def compact_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "segment_id": segment.get("id"),
            "kind": segment.get("kind"),
            "text": segment.get("text"),
            "page": (segment.get("locator") or {}).get("page"),
        }
        for segment in segments
    ]


def infer_source_type(source_metadata: dict[str, Any]) -> str:
    mime_type = str(source_metadata.get("mime_type") or "").lower()
    filename = str(source_metadata.get("filename") or "").lower()

    if "pdf" in mime_type or filename.endswith(".pdf"):
        return "pdf"
    if "word" in mime_type or filename.endswith(".docx"):
        return "docx"
    if "markdown" in mime_type or filename.endswith((".md", ".markdown")):
        return "markdown"

    return "txt"
