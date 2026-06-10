from __future__ import annotations

import json
from typing import Any

from app.intellex.models import ParsedDocument
from app.intellex.skills.models import SourceResearchOutput
from app.intellex.text_sampling import sample_text_for_research
from app.services.openai_client import OpenAIClient
from app.services.web_research import WebResearchClient, build_research_query

DOCUMENT_SYSTEM_PROMPT = """You extract bibliographic metadata from parsed document text.

Rules:
- Use only evidence from the provided document text for document-origin fields.
- Prefer official titles, designators, issuing authorities, authors, versions, and publication dates printed in the document.
- Classify document_type as one of: military_doctrine, research_paper, white_paper, report, unknown.
- publication_date_in_document must be an ISO-8601 date (YYYY-MM-DD) when possible, otherwise null.
- publication_date_public should be null in this step unless the document text itself states a public release date to constituents.
- source_url should be null unless a URL is printed in the document text.
- Provide per-field confidence from 0.0 to 1.0.
- Set provenance for each populated field to "document".
- Return valid JSON only."""

DOCUMENT_USER_TEMPLATE = """Filename: {filename}
MIME type: {mime_type}

Document text sample:
{document_text}

Return JSON with keys:
document_type, title, identifier, issuing_authority, authors, version,
publication_date_in_document, publication_date_public, source_url, abstract,
confidence, provenance"""

WEB_SYSTEM_PROMPT = """You fill missing bibliographic metadata using web search snippets.

Rules:
- Only fill fields that are null or low-confidence in the document draft.
- Do not overwrite high-confidence document values.
- publication_date_public is the date the document was published to its audience or public web.
- source_url should be the best canonical public URL when available.
- Set provenance to "web" for fields filled from web snippets.
- Keep existing provenance "document" for unchanged fields.
- Return valid JSON only."""

WEB_USER_TEMPLATE = """Document draft metadata:
{document_metadata}

Web search results:
{web_results}

Return the updated metadata JSON with the same keys as the draft."""


class SourceResearchSkill:
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
        document_text = sample_text_for_research(
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

        if self._needs_web_gap_fill(draft) and self.web_client.enabled:
            query = build_research_query(
                title=draft.title,
                identifier=draft.identifier,
            )

            if query:
                web_sources = self.web_client.search(query)
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

        elif self._needs_web_gap_fill(draft) and not draft.publication_date_public:
            draft.publication_date_public = draft.publication_date_in_document
            if draft.publication_date_in_document:
                draft.provenance["publication_date_public"] = "inferred"

        return draft, {
            "model": model,
            "token_usage": token_usage,
        }

    def _needs_web_gap_fill(self, draft: SourceResearchOutput) -> bool:
        if not draft.publication_date_public:
            return True

        if not draft.source_url:
            return True

        if not draft.issuing_authority and draft.document_type == "military_doctrine":
            return True

        low_confidence_publication = draft.confidence.get("publication_date_public", 1.0) < 0.75
        return low_confidence_publication
