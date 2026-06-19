from __future__ import annotations

import json
from typing import Any

from app.intellex.metadata_slice import build_metadata_slice
from app.intellex.models import ParsedDocument
from app.intellex.stages.models import SourceResearchOutput
from app.services.openai_client import OpenAIClient
from app.services.web_research import WebResearchClient, build_research_query

DOCUMENT_SYSTEM_PROMPT = """You extract bibliographic metadata from the early pages of a parsed document.

Extract ONLY these document-origin fields from the provided text:
- title
- issuing_authority
- version
- publication_date_in_document (ISO-8601 YYYY-MM-DD when possible, otherwise null)
- distribution_line (distribution / dissemination / releasability statement when present)
- abstract (brief description of the document's subject and purpose, 1-2 sentences maximum; null if not inferable from the text)

Rules:
- Use only evidence from the provided document text.
- Leave other fields null or empty unless explicitly present in the text.
- document_type may be inferred when obvious (military_doctrine, research_paper, white_paper, report, unknown).
- Provide per-field confidence from 0.0 to 1.0 for populated fields.
- Set provenance to "document" for populated fields.
- Return valid JSON only."""

DOCUMENT_USER_TEMPLATE = """Filename: {filename}
MIME type: {mime_type}

Metadata slice (early pages):
{document_text}

Return JSON with keys:
document_type, title, identifier, issuing_authority, authors, version,
publication_date_in_document, publication_date_public, source_url, abstract,
distribution_line, confidence, provenance"""

WEB_SYSTEM_PROMPT = """You fill missing bibliographic metadata using web search snippets.

Rules:
- Only fill title or issuing_authority when null or low-confidence in the document draft.
- Do not overwrite high-confidence document values.
- Set provenance to "web" for fields filled from web snippets.
- Keep existing provenance "document" for unchanged fields.
- Return valid JSON only."""

WEB_USER_TEMPLATE = """Document draft metadata:
{document_metadata}

Web search results:
{web_results}

Return the updated metadata JSON with the same keys as the draft."""


class SourceResearchStage:
    def __init__(
        self,
        *,
        openai_client: OpenAIClient | None = None,
        web_client: WebResearchClient | None = None,
        max_document_chars: int = 12_000,
    ) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.web_client = web_client or WebResearchClient()
        self.max_document_chars = max_document_chars

    def run(
        self,
        *,
        filename: str,
        mime_type: str,
        parsed_document: ParsedDocument,
    ) -> tuple[SourceResearchOutput, dict[str, Any]]:
        # SECURITY: Only a bounded metadata slice from early pages is sent to the model.
        document_text = build_metadata_slice(
            parsed_document,
            max_chars=self.max_document_chars,
        )

        if not document_text:
            raise RuntimeError("Parsed document contains no text for source research.")

        document_result = self.openai_client.complete_json(
            system_prompt=DOCUMENT_SYSTEM_PROMPT,
            user_prompt=DOCUMENT_USER_TEMPLATE.format(
                filename=filename,
                mime_type=mime_type,
                document_text=document_text,
            ),
        )
        draft = SourceResearchOutput.model_validate(document_result.content)

        token_usage = dict(document_result.token_usage)
        model = document_result.model
        web_sources: list[dict[str, str]] = []
        web_search_count = 0

        if self._needs_web_gap_fill(draft) and self.web_client.enabled:
            query = build_research_query(
                title=draft.title,
                identifier=draft.identifier,
            )

            if query:
                web_sources = self.web_client.search(query)
                web_search_count = 1
                web_result = self.openai_client.complete_json(
                    system_prompt=WEB_SYSTEM_PROMPT,
                    user_prompt=WEB_USER_TEMPLATE.format(
                        document_metadata=json.dumps(draft.model_dump(), indent=2),
                        web_results=json.dumps(web_sources, indent=2),
                    ),
                )
                draft = SourceResearchOutput.model_validate(web_result.content)
                draft.web_sources = web_sources

                for key, value in web_result.token_usage.items():
                    token_usage[key] = token_usage.get(key, 0) + value

        return draft, {
            "model": model,
            "token_usage": token_usage,
            "web_search_count": web_search_count,
        }

    def _needs_web_gap_fill(self, draft: SourceResearchOutput) -> bool:
        if not draft.title or draft.title == "Untitled document":
            return True

        if draft.confidence.get("title", 1.0) < 0.75:
            return True

        if not draft.issuing_authority:
            return True

        return draft.confidence.get("issuing_authority", 1.0) < 0.75
