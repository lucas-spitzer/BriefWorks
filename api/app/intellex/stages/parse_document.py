from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.intellex.ingest import parse_source_content
from app.intellex.models import ParseResult, ParsedDocument
from app.services.llamaparse_client import LlamaParseClient


@dataclass(frozen=True)
class ParseOutput:
    document: ParsedDocument
    raw_markdown: str
    api_payload: dict[str, Any]
    structured_pages: list[dict[str, Any]]
    page_count: int
    line_count: int
    parser: str
    job_id: str | None

    def to_stage_output(self, *, raw_markdown_path: str) -> dict[str, Any]:
        return {
            "summary": (
                f"Parsed {self.page_count} page(s) into {self.line_count} line(s) "
                f"via {self.parser}."
            ),
            "page_count": self.page_count,
            "line_count": self.line_count,
            "parser": self.parser,
            "job_id": self.job_id,
            "raw_markdown_path": raw_markdown_path,
            "api_response": self.api_payload,
        }


class ParseStage:
    def __init__(self, *, llamaparse_client: LlamaParseClient | None = None) -> None:
        self.llamaparse_client = llamaparse_client or LlamaParseClient()

    def run(
        self,
        *,
        mime_type: str,
        filename: str,
        content: bytes,
    ) -> tuple[ParseOutput, dict[str, Any]]:
        parse_result: ParseResult = parse_source_content(
            mime_type=mime_type,
            filename=filename,
            content=content,
            llamaparse_client=self.llamaparse_client,
        )
        document = parse_result.document

        output = ParseOutput(
            document=document,
            raw_markdown=parse_result.raw_markdown,
            api_payload=parse_result.api_payload,
            structured_pages=parse_result.structured_pages,
            page_count=document.page_count,
            line_count=len(document.lines),
            parser=document.parser,
            job_id=document.job_id,
        )
        execution = {
            "model": "llamaparse",
            "token_usage": {},
            "page_count": document.page_count,
            "llamaparse_job_id": document.job_id,
            "api_response": parse_result.api_payload,
        }
        return output, execution
