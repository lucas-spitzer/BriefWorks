"""Validate markdown or PDF uploads for study-sheet generation."""

from __future__ import annotations

from app.services.source_upload import (
    MAX_FILENAME_LENGTH,
    PDF_MAGIC,
    SourceUploadValidationError,
    sanitize_upload_filename,
)

PDF_MIME_TYPES = frozenset({"application/pdf", "application/x-pdf"})
MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown"})
PDF_EXTENSIONS = frozenset({".pdf"})


class StudySheetUploadError(ValueError):
    """Raised when a study-sheet upload fails validation."""


def validate_study_sheet_upload(
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
    max_markdown_chars: int,
) -> tuple[str, str]:
    """Return ``(safe_filename, mime_type)`` for a markdown or PDF upload."""
    if not filename:
        raise StudySheetUploadError("Uploaded file must include a filename.")

    if not content:
        raise StudySheetUploadError("Uploaded file is empty.")

    if len(content) > max_bytes:
        max_megabytes = max_bytes // (1024 * 1024)
        raise StudySheetUploadError(
            f"Uploaded file exceeds the {max_megabytes} MB limit.",
        )

    try:
        safe_filename = sanitize_upload_filename(filename)
    except SourceUploadValidationError as exc:
        raise StudySheetUploadError(str(exc)) from exc

    mime_type = _resolve_mime(
        filename=safe_filename,
        content_type=content_type,
        content=content,
        max_markdown_chars=max_markdown_chars,
    )
    return safe_filename, mime_type


def _resolve_mime(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
    max_markdown_chars: int,
) -> str:
    declared = (content_type or "").split(";", 1)[0].strip().lower()
    lower = filename.lower()

    if lower.endswith(tuple(PDF_EXTENSIONS)) or declared in PDF_MIME_TYPES:
        if not content.startswith(PDF_MAGIC):
            raise StudySheetUploadError("Uploaded file is not a valid PDF.")
        return "application/pdf"

    if lower.endswith(tuple(MARKDOWN_EXTENSIONS)):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StudySheetUploadError(
                "Markdown must be valid UTF-8.",
            ) from exc
        if len(text) > max_markdown_chars:
            raise StudySheetUploadError(
                "Markdown is too large for a two-page sheet.",
            )
        return "text/markdown"

    raise StudySheetUploadError(
        "Only markdown (.md) and PDF files are supported.",
    )


def decode_markdown(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StudySheetUploadError("Markdown must be valid UTF-8.") from exc


# Re-export so callers can share the filename length cap.
__all__ = [
    "MAX_FILENAME_LENGTH",
    "StudySheetUploadError",
    "decode_markdown",
    "validate_study_sheet_upload",
]
