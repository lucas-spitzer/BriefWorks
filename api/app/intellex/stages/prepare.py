from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any

from app.config import get_settings

from app.intellex.line_content_filter import pre_filter_lines, validate_prepared_document
from app.intellex.models import ParsedDocument, ParsedLine
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You extract learning content from parsed documents.

Your ONLY goal: keep chapter/section headings and the body text that teaches the subject under each heading.

KEEP:
- Chapter, section, part, unit, and lesson headings at any level
- Numbered doctrinal paragraphs and lists that teach the subject matter
- Tables and lists that are part of the main instructional content

REMOVE everything else, including:
- Title pages, half titles, colophons, imprints
- Table of contents and TOC dot-leader lines
- Lists of figures, tables, illustrations, abbreviations, acronyms, maps, or plates
- Preface, foreword, dedication, acknowledgments, about-the-author
- Distribution statements, disclaimers, distribution restrictions
- Glossaries, terms-and-definitions, acronyms-and-abbreviations sections
- Indexes, bibliographies, references, works cited, further reading
- Appendices, errata, record of changes, summary of changes
- Notes, endnotes, footnotes sections
- Synopsis, executive summary, copyright notices
- Page numbers, running headers/footers, blank-page notices
- Figure/table captions, bare citation markers, isolated URLs or DOIs
- Administrative boilerplate and front/back matter

Return valid JSON only with keys:
- exclude_line_ids: array of line_id strings to remove
- exclude_pages: array of integer page numbers to remove entirely
- reasons: object mapping line_id or "page:<n>" to a short reason label"""

USER_TEMPLATE = """Document pages (batch {batch_index} of {batch_total}):

{pages_json}

Return JSON with exclude_line_ids, exclude_pages, and reasons."""

_LINE_PREVIEW_FULL_TEXT_THRESHOLD = 500
_LONG_LINE_PREVIEW_CHARS = 800


@dataclass(frozen=True)
class PrepareBatchDecision:
    exclude_line_ids: set[str]
    exclude_pages: set[int]
    reasons: dict[str, str]


@dataclass(frozen=True)
class PrepareOutput:
    prepared_document: ParsedDocument
    excluded_line_ids: list[str]
    excluded_pages: list[int]
    reasons: dict[str, str]
    kept_line_count: int
    excluded_line_count: int
    pre_filter_report: dict[str, Any]
    validation_report: dict[str, Any]


class PrepareStage:
    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        batch_pages: int | None = None,
    ) -> None:
        self._llm_client = llm_client
        self.batch_pages = batch_pages or get_settings().intellex.prepare_batch_pages

    @property
    def llm_client(self) -> LLMClient:
        # Resolved lazily so workspace overrides set at run time are honored.
        if self._llm_client is None:
            self._llm_client = get_llm_client("prepare")
        return self._llm_client

    def run(self, *, parsed_document: ParsedDocument) -> tuple[PrepareOutput, dict[str, Any]]:
        if not parsed_document.lines:
            raise RuntimeError("Parsed document contains no lines to prepare.")

        candidate_lines, pre_filter_report = pre_filter_lines(parsed_document)

        if not candidate_lines:
            raise RuntimeError(
                "Prepare pre-filter removed all document lines; nothing remains for learning content.",
            )

        candidate_document = ParsedDocument(
            page_count=parsed_document.page_count,
            lines=candidate_lines,
            parser=parsed_document.parser,
            job_id=parsed_document.job_id,
        )

        pages = sorted({line.page for line in candidate_lines})
        batches = [
            pages[index : index + self.batch_pages]
            for index in range(0, len(pages), self.batch_pages)
        ]

        exclude_line_ids: set[str] = set(pre_filter_report.get("excluded_line_ids", []))
        exclude_pages: set[int] = set()
        reasons: dict[str, str] = {}
        token_usage: dict[str, int] = {}
        model = self.llm_client.model

        for batch_index, batch_pages in enumerate(batches, start=1):
            batch_lines = [line for line in candidate_lines if line.page in batch_pages]
            decision, execution = self._run_batch(
                lines=batch_lines,
                batch_index=batch_index,
                batch_total=len(batches),
            )
            model = execution["model"]

            for key, value in execution["token_usage"].items():
                token_usage[key] = token_usage.get(key, 0) + value

            exclude_line_ids.update(decision.exclude_line_ids)
            exclude_pages.update(decision.exclude_pages)
            reasons.update(decision.reasons)

        prepared_lines = [
            line
            for line in parsed_document.lines
            if line.line_id not in exclude_line_ids and line.page not in exclude_pages
        ]

        if not prepared_lines:
            raise RuntimeError(
                "Prepare step removed all document lines; nothing remains for learning content.",
            )

        prepared_document = ParsedDocument(
            page_count=max(line.page for line in prepared_lines),
            lines=prepared_lines,
            parser=parsed_document.parser,
            job_id=parsed_document.job_id,
        )

        validation_report = validate_prepared_document(prepared_document)

        output = PrepareOutput(
            prepared_document=prepared_document,
            excluded_line_ids=sorted(exclude_line_ids),
            excluded_pages=sorted(exclude_pages),
            reasons=reasons,
            kept_line_count=len(prepared_lines),
            excluded_line_count=len(parsed_document.lines) - len(prepared_lines),
            pre_filter_report=pre_filter_report,
            validation_report=validation_report,
        )

        return output, {
            "model": model,
            "token_usage": token_usage,
            "batch_count": len(batches),
        }

    def _line_preview(self, text: str) -> str:
        if len(text) <= _LINE_PREVIEW_FULL_TEXT_THRESHOLD:
            return text
        return text[:_LONG_LINE_PREVIEW_CHARS]

    def _run_batch(
        self,
        *,
        lines: list[ParsedLine],
        batch_index: int,
        batch_total: int,
    ) -> tuple[PrepareBatchDecision, dict[str, Any]]:
        pages_payload: dict[str, list[dict[str, Any]]] = {}

        for line in lines:
            pages_payload.setdefault(str(line.page), []).append(
                {
                    "line_id": line.line_id,
                    "kind": line.kind or "paragraph",
                    "text": self._line_preview(line.text),
                },
            )

        result = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                batch_index=batch_index,
                batch_total=batch_total,
                pages_json=json.dumps(pages_payload, indent=2),
            ),
        )

        exclude_line_ids = {
            str(line_id)
            for line_id in result.content.get("exclude_line_ids", [])
            if line_id
        }
        exclude_pages = {
            int(page)
            for page in result.content.get("exclude_pages", [])
            if isinstance(page, int) or str(page).isdigit()
        }
        raw_reasons = result.content.get("reasons") or {}
        reasons = {
            str(key): str(value)
            for key, value in raw_reasons.items()
            if value
        }

        return (
            PrepareBatchDecision(
                exclude_line_ids=exclude_line_ids,
                exclude_pages=exclude_pages,
                reasons=reasons,
            ),
            {
                "model": result.model,
                "token_usage": result.token_usage,
            },
        )


def summarize_prepare_reasons(reasons: dict[str, str]) -> dict[str, int]:
    counts: Counter[str] = Counter()

    for reason in reasons.values():
        counts[reason] += 1

    return dict(counts)
