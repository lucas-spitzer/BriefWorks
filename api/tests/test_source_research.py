from app.intellex.metadata_slice import build_metadata_slice
from app.intellex.models import ParsedDocument, ParsedLine
from app.intellex.stages.models import SourceResearchOutput
from app.intellex.stages.promotion import merge_research_into_source_metadata
from app.intellex.stages.source_research import SourceResearchStage
from app.services.openai_client import OpenAICompletionResult


class FakeOpenAIClient:
    def __init__(self, document_payload: dict, web_payload: dict | None = None) -> None:
        self.document_payload = document_payload
        self.web_payload = web_payload or document_payload
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        self.calls += 1

        if "Web search results" in user_prompt:
            payload = self.web_payload
        else:
            payload = self.document_payload

        return OpenAICompletionResult(
            content=payload,
            model="gpt-4o-mini",
            token_usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )


class DisabledWebClient:
    enabled = False

    def search(self, query: str, *, max_results: int = 5) -> list[dict[str, str]]:
        return []


def test_build_metadata_slice_prefers_early_pages() -> None:
    document = ParsedDocument(
        page_count=10,
        lines=[
            ParsedLine(text="MCDP 1 Warfighting", page=1, font_size=16.0),
            ParsedLine(text="United States Marine Corps", page=1, font_size=12.0),
            ParsedLine(text="Late page content", page=9, font_size=12.0),
        ],
    )

    sample = build_metadata_slice(document, max_chars=500)

    assert "MCDP 1 Warfighting" in sample
    assert "Late page content" not in sample


def test_merge_research_into_source_metadata_preserves_parse_block() -> None:
    research = SourceResearchOutput(
        document_type="military_doctrine",
        title="Warfighting",
        identifier="MCDP 1",
        issuing_authority="US Marine Corps",
        publication_date_in_document="1997-06-20",
        publication_date_public="1997-06-20",
        distribution_line="Approved for public release; distribution is unlimited.",
        confidence={"title": 0.98},
        provenance={"title": "document"},
    )

    merged = merge_research_into_source_metadata(
        {"parse": {"page_count": 96}},
        research,
        researched_at="2026-06-08T00:00:00+00:00",
    )

    assert merged["parse"]["page_count"] == 96
    assert merged["research"]["title"] == "Warfighting"
    assert merged["research"]["identifier"] == "MCDP 1"
    assert merged["research"]["distribution_line"].startswith("Approved")


def test_source_research_stage_extracts_metadata_slice_fields() -> None:
    document = ParsedDocument(
        page_count=1,
        lines=[ParsedLine(text="MCDP 1 Warfighting", page=1, font_size=12.0)],
    )
    stage = SourceResearchStage(
        openai_client=FakeOpenAIClient(
            {
                "document_type": "military_doctrine",
                "title": "Warfighting",
                "identifier": "MCDP 1",
                "issuing_authority": "US Marine Corps",
                "authors": [],
                "version": "1997",
                "publication_date_in_document": "1997-06-20",
                "publication_date_public": None,
                "source_url": None,
                "abstract": "Foundational Marine Corps doctrine on the theory and practice of warfighting.",
                "distribution_line": "Approved for public release; distribution is unlimited.",
                "confidence": {"title": 0.98},
                "provenance": {"title": "document"},
            },
        ),
        web_client=DisabledWebClient(),
    )

    output, execution = stage.run(
        filename="mcdp1.pdf",
        mime_type="application/pdf",
        parsed_document=document,
    )

    assert output.title == "Warfighting"
    assert output.abstract == "Foundational Marine Corps doctrine on the theory and practice of warfighting."
    assert output.distribution_line.startswith("Approved")
    assert execution["token_usage"]["total_tokens"] == 150
