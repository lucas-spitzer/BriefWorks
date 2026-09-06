"""Generate a one- or two-page study sheet PDF from a source file."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.mathesys.study_sheet.html import sanitize_body_html, wrap_sheet_html
from app.mathesys.study_sheet.printer import PdfPrinter
from app.mathesys.study_sheet.prompts import (
    SYSTEM_PROMPT,
    retry_note,
    user_prompt_for_markdown,
    user_prompt_for_pdf,
)
from app.mathesys.study_sheet.upload import decode_markdown
from app.services.llm.base import LLMCompletionResult

PDF_MIME = "application/pdf"
MAX_PAGES = 2
MIN_PAGES = 1
DEFAULT_MAX_ATTEMPTS = 3


class StudySheetError(Exception):
    """Generation failed for a reason the operator can act on."""


class StudySheetFitError(StudySheetError):
    """HTML did not fit the two-page budget after retries."""


@dataclass(frozen=True)
class StudySheetSource:
    filename: str
    mime_type: str
    content: bytes

    @property
    def is_pdf(self) -> bool:
        return self.mime_type == PDF_MIME or self.filename.lower().endswith(".pdf")


@dataclass(frozen=True)
class StudySheetResult:
    title: str
    html: str
    pdf: bytes
    page_count: int
    attempt_count: int
    model: str
    provider: str
    token_usages: list[dict[str, int]] = field(default_factory=list)


class StudySheetCompleter(Protocol):
    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> LLMCompletionResult: ...


def generate_study_sheet(
    *,
    source: StudySheetSource,
    completer: StudySheetCompleter,
    printer: PdfPrinter,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> StudySheetResult:
    """Ask the model for body HTML, wrap it, print, and retry if over two pages."""
    usages: list[dict[str, int]] = []
    last_model = ""
    last_provider = ""
    last_page_count = 0
    fit_error = "Study sheet did not fit on two pages."

    for attempt in range(1, max_attempts + 1):
        note = None if attempt == 1 else retry_note(
            page_count=last_page_count,
            max_pages=MAX_PAGES,
        )
        completion = _complete(source=source, completer=completer, retry_note=note)
        usages.append(dict(completion.token_usage))
        last_model = completion.model
        last_provider = completion.provider

        title, body_html = _parse_sheet_payload(
            completion.content,
            fallback_title=_filename_stem(source.filename),
        )
        html = wrap_sheet_html(title=title, body_html=body_html)
        pdf = printer.print_html(html)
        page_count = printer.page_count(pdf)
        last_page_count = page_count

        if MIN_PAGES <= page_count <= MAX_PAGES:
            return StudySheetResult(
                title=title,
                html=html,
                pdf=pdf,
                page_count=page_count,
                attempt_count=attempt,
                model=last_model,
                provider=last_provider,
                token_usages=usages,
            )

        fit_error = (
            f"Sheet printed at {page_count} pages; budget is {MAX_PAGES}."
        )

    raise StudySheetFitError(fit_error)


def _complete(
    *,
    source: StudySheetSource,
    completer: StudySheetCompleter,
    retry_note: str | None,
) -> LLMCompletionResult:
    if source.is_pdf:
        complete_document = getattr(completer, "complete_json_with_document", None)
        if complete_document is None:
            raise StudySheetError(
                "PDF study sheets require a model that accepts documents.",
            )
        return complete_document(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt_for_pdf(
                filename=source.filename,
                retry_note=retry_note,
            ),
            document_bytes=source.content,
            document_mime=PDF_MIME,
        )

    text = decode_markdown(source.content)
    return completer.complete_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt_for_markdown(
            filename=source.filename,
            text=text,
            retry_note=retry_note,
        ),
    )


def _parse_sheet_payload(
    content: dict[str, Any],
    *,
    fallback_title: str,
) -> tuple[str, str]:
    title_raw = content.get("title")
    title = title_raw.strip() if isinstance(title_raw, str) else ""
    if not title:
        title = fallback_title or "Study sheet"

    body_raw = content.get("body_html")
    if not isinstance(body_raw, str) or not body_raw.strip():
        raise StudySheetError("Model did not return study-sheet HTML.")

    body_html = sanitize_body_html(body_raw)
    if not body_html:
        raise StudySheetError("Study-sheet HTML was empty after sanitizing.")
    return title, body_html


def _filename_stem(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1]
    if "." in name:
        return name.rsplit(".", 1)[0]
    return name or "Study sheet"
