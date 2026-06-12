from __future__ import annotations

import os
import re

from app.intellex.ingest import PDF_MIME_TYPES

PDF_MAGIC = b"%PDF-"
MAX_FILENAME_LENGTH = 255
_INVALID_FILENAME_CHARS = re.compile(r"[^\w.\- ()]")


class SourceUploadValidationError(ValueError):
    """Raised when an uploaded source file fails validation."""


def sanitize_upload_filename(filename: str) -> str:
    """Return a basename-only filename safe for storage paths."""
    basename = os.path.basename(filename.strip())

    if not basename or basename in {".", ".."}:
        raise SourceUploadValidationError("Uploaded file must include a valid filename.")

    if "/" in basename or "\\" in basename or ".." in basename:
        raise SourceUploadValidationError("Filename must not contain path separators.")

    if len(basename) > MAX_FILENAME_LENGTH:
        raise SourceUploadValidationError(
            f"Filename must be {MAX_FILENAME_LENGTH} characters or fewer.",
        )

    if _INVALID_FILENAME_CHARS.search(basename):
        raise SourceUploadValidationError(
            "Filename contains unsupported characters.",
        )

    return basename


def resolve_source_mime_type(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> str:
    """Resolve and validate MIME type for an uploaded PDF source."""
    if not content.startswith(PDF_MAGIC):
        raise SourceUploadValidationError(
            "Uploaded file is not a valid PDF.",
        )

    declared_type = (content_type or "").split(";", 1)[0].strip().lower()
    filename_lower = filename.lower()

    if declared_type in PDF_MIME_TYPES or filename_lower.endswith(".pdf"):
        return declared_type if declared_type in PDF_MIME_TYPES else "application/pdf"

    raise SourceUploadValidationError(
        "Only PDF sources are supported.",
    )


def validate_source_upload(
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
) -> tuple[str, str]:
    """Validate upload input and return (safe_filename, mime_type)."""
    if not filename:
        raise SourceUploadValidationError("Uploaded file must include a filename.")

    if not content:
        raise SourceUploadValidationError("Uploaded file is empty.")

    if len(content) > max_bytes:
        max_megabytes = max_bytes // (1024 * 1024)
        raise SourceUploadValidationError(
            f"Uploaded file exceeds the {max_megabytes} MB limit.",
        )

    safe_filename = sanitize_upload_filename(filename)
    mime_type = resolve_source_mime_type(
        filename=safe_filename,
        content_type=content_type,
        content=content,
    )

    return safe_filename, mime_type
