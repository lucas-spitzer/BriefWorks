import pytest

from app.services.source_upload import (
    SourceUploadValidationError,
    sanitize_upload_filename,
    validate_source_upload,
)

PDF_BYTES = b"%PDF-1.4 minimal"


def test_sanitize_upload_filename_strips_directory_components() -> None:
    assert sanitize_upload_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_upload_filename("folder/report.pdf") == "report.pdf"


def test_sanitize_upload_filename_rejects_empty_name() -> None:
    with pytest.raises(SourceUploadValidationError):
        sanitize_upload_filename("../")


def test_validate_source_upload_accepts_pdf() -> None:
    filename, mime_type = validate_source_upload(
        filename="report.pdf",
        content_type="application/pdf",
        content=PDF_BYTES,
        max_bytes=1024,
    )

    assert filename == "report.pdf"
    assert mime_type == "application/pdf"


def test_validate_source_upload_rejects_non_pdf_content() -> None:
    with pytest.raises(SourceUploadValidationError, match="not a valid PDF"):
        validate_source_upload(
            filename="report.pdf",
            content_type="application/pdf",
            content=b"not-a-pdf",
            max_bytes=1024,
        )


def test_validate_source_upload_rejects_oversized_file() -> None:
    with pytest.raises(SourceUploadValidationError, match="exceeds the"):
        validate_source_upload(
            filename="report.pdf",
            content_type="application/pdf",
            content=PDF_BYTES,
            max_bytes=4,
        )
