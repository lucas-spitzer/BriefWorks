from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.intellex.metadata_slice import build_source_research_slices
from app.intellex.models import ParsedDocument
from app.intellex.stages.models import SourceResearchOutput
from app.services.llm import LLMClient, get_llm_client

SYSTEM_PROMPT = """You extract a source profile from labeled sections of a parsed professional document (doctrine, scientific papers, white papers, technical manuals, standards, policies, legal documents, theses, books, reports).

Extract bibliographic fields from document evidence:
- title: the document's own title, not a running header or series name
- identifier: the document's formal identifier in its genre's convention — publication number (e.g. "MCDP 1", "JP 3-0"), DOI, ISBN, report number, standard number (e.g. "ISO 9001:2015"), docket/case number, or arXiv id
- issuing_authority: the organization that issued it — agency or service branch for doctrine/policy, journal or conference for papers, publisher for books, standards body for standards, company for white papers and manuals
- authors: named individual authors when listed (common in papers, theses, books; often absent in doctrine and standards)
- version: edition, revision, change number, or draft designation (e.g. "2nd edition", "Rev. C", "Change 1", "v2.1")
- publication_date_in_document (ISO-8601 YYYY-MM-DD when possible, otherwise null)
- publication_date_public and source_url only when explicitly printed in the document
- distribution_line (distribution / dissemination / releasability / copyright-restriction statement when present)

Extract interpretive fields:
- purpose: why the document exists
- target_audience: intended readers
- scope: what the document covers and any stated boundaries
- abstract: 2-3 sentence summary of subject and purpose. If the document prints its own abstract (typical for papers and theses), condense that faithfully instead of writing a new one.

Rules:
- Use only evidence from the provided sections. Filename is a weak hint when cover text is sparse.
- document_type may be inferred when obvious (military_doctrine, research_paper, white_paper, report, technical_manual, standard, policy, legal_document, thesis, book, unknown).
- Prefer preface/foreword/introduction/abstract/executive summary for purpose, target_audience, and scope.
- Infer purpose, audience, or scope from TOC/structure only when not stated explicitly; mark those as provenance "inferred" with lower confidence.
- Set provenance to "document" for values taken directly from the text.
- Do not mistake boilerplate for profile fields: running headers, journal citation lines for OTHER works, and template text are not evidence.
- Leave fields null when not supported by evidence.
- Provide per-field confidence from 0.0 to 1.0 for populated fields.
- Return valid JSON only."""

USER_TEMPLATE = """Filename: {filename}
MIME type: {mime_type}

## Cover
{cover}

## Preface / Foreword / Introduction / Abstract
{preface}

## Table of Contents
{toc}

## Additional early pages
{remainder}

Return JSON with keys:
document_type, title, identifier, issuing_authority, authors, version,
publication_date_in_document, publication_date_public, source_url, abstract,
distribution_line, purpose, target_audience, scope, confidence, provenance"""


def _section_or_placeholder(text: str) -> str:
    return text.strip() if text.strip() else "(not found in document)"


class SourceResearchStage:
    def __init__(
        self,
        *,
        llm_client: LLMClient | None = None,
        max_document_chars: int | None = None,
    ) -> None:
        self._llm_client = llm_client
        self.max_document_chars = max_document_chars or get_settings().intellex.source_research_max_chars

    @property
    def llm_client(self) -> LLMClient:
        # Resolved lazily so workspace overrides set at run time are honored.
        if self._llm_client is None:
            self._llm_client = get_llm_client("source_research")
        return self._llm_client

    def run(
        self,
        *,
        filename: str,
        mime_type: str,
        parsed_document: ParsedDocument,
    ) -> tuple[SourceResearchOutput, dict[str, Any]]:
        # SECURITY: Only bounded metadata slices from early pages are sent to the model.
        slices = build_source_research_slices(
            parsed_document,
            max_chars=self.max_document_chars,
        )

        if not any(slices.values()):
            raise RuntimeError("Parsed document contains no text for source research.")

        result = self.llm_client.complete_json(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_TEMPLATE.format(
                filename=filename,
                mime_type=mime_type,
                cover=_section_or_placeholder(slices["cover"]),
                preface=_section_or_placeholder(slices["preface"]),
                toc=_section_or_placeholder(slices["toc"]),
                remainder=_section_or_placeholder(slices["remainder"]),
            ),
        )
        output = SourceResearchOutput.model_validate(result.content)

        return output, {
            "model": result.model,
            "provider": getattr(result, "provider", None),
            "token_usage": dict(result.token_usage),
        }
