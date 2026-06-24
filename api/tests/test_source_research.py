from app.intellex.models import ParsedDocument, ParsedLine
from app.intellex.stages.models import SourceResearchOutput
from app.intellex.stages.promotion import merge_research_into_source_metadata
from app.intellex.stages.source_research import SourceResearchStage
from app.services.openai_client import OpenAICompletionResult


class FakeOpenAIClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        self.calls += 1

        return OpenAICompletionResult(
            content=self.payload,
            model="gpt-4o-mini",
            token_usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )


def test_merge_research_into_source_metadata_preserves_parse_block() -> None:
    research = SourceResearchOutput(
        document_type="military_doctrine",
        title="Warfighting",
        identifier="MCDP 1",
        issuing_authority="US Marine Corps",
        publication_date_in_document="1997-06-20",
        publication_date_public="1997-06-20",
        distribution_line="Approved for public release; distribution is unlimited.",
        purpose="Describe Marine Corps warfighting doctrine.",
        target_audience="Marine Corps commanders and staffs",
        scope="Theory and practice of warfighting across the MAGTF.",
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
    assert merged["research"]["purpose"].startswith("Describe Marine Corps")


def test_source_research_stage_extracts_profile_fields() -> None:
    document = ParsedDocument(
        page_count=3,
        lines=[
            ParsedLine(text="MCDP 1 Warfighting", page=1, font_size=12.0),
            ParsedLine(text="Preface", page=2, kind="heading"),
            ParsedLine(text="This publication is for all Marines.", page=2),
        ],
    )
    client = FakeOpenAIClient(
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
            "purpose": "Establish foundational warfighting doctrine.",
            "target_audience": "All Marines",
            "scope": "Marine Corps warfighting across the MAGTF.",
            "confidence": {"title": 0.98},
            "provenance": {"title": "document"},
        },
    )
    stage = SourceResearchStage(llm_client=client)

    output, execution = stage.run(
        filename="mcdp1.pdf",
        mime_type="application/pdf",
        parsed_document=document,
    )

    assert client.calls == 1
    assert output.title == "Warfighting"
    assert output.abstract == "Foundational Marine Corps doctrine on the theory and practice of warfighting."
    assert output.purpose == "Establish foundational warfighting doctrine."
    assert output.target_audience == "All Marines"
    assert output.scope.startswith("Marine Corps warfighting")
    assert output.distribution_line.startswith("Approved")
    assert execution["token_usage"]["total_tokens"] == 150
