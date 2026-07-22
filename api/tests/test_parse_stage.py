from unittest.mock import MagicMock

import pytest

from app.intellex.stages.parse_document import ParseStage
from app.services.llamaparse_client import LlamaParsePage, LlamaParseResult


def test_parse_stage_returns_json_api_response() -> None:
    llamaparse_client = MagicMock()
    llamaparse_client.parse_pdf.return_value = LlamaParseResult(
        job_id="job-123",
        pages=[LlamaParsePage(page=1, markdown="# Title\n\nBody paragraph.")],
        raw_markdown="<!-- page:1 -->\n# Title\n\nBody paragraph.",
        api_payload={
            "job": {"id": "job-123", "status": "COMPLETED"},
            "pages": [{"page": 1, "markdown_length": 24}],
        },
        structured_pages=[{"page_number": 1, "items": [{"type": "heading", "md": "# Title"}]}],
    )

    stage = ParseStage(llamaparse_client=llamaparse_client)
    output, execution = stage.run(
        mime_type="application/pdf",
        filename="sample.pdf",
        content=b"%PDF-1.4",
    )

    assert output.parser == "llamaparse"
    assert output.job_id == "job-123"
    assert output.page_count == 1
    assert output.line_count >= 1
    assert output.api_payload["job"]["status"] == "COMPLETED"
    assert len(output.structured_pages) == 1
    assert execution["model"] == "llamaparse"
    assert execution["page_count"] == 1
    assert execution["api_response"]["job"]["id"] == "job-123"

    stage_output = output.to_stage_output(raw_markdown_path="workspaces/ws/sources/src/parse/raw.md")
    assert stage_output["api_response"]["pages"][0]["page"] == 1
    assert stage_output["raw_markdown_path"].endswith("parse/raw.md")
    assert "summary" in stage_output


def test_parse_stage_rejects_non_pdf() -> None:
    stage = ParseStage(llamaparse_client=MagicMock())

    with pytest.raises(ValueError, match="Only PDF sources are supported"):
        stage.run(
            mime_type="text/plain",
            filename="notes.txt",
            content=b"hello",
        )
