import pytest

from app.intellex.line_content_filter import pre_filter_lines, validate_prepared_document
from app.intellex.models import ParsedDocument, ParsedLine
from app.intellex.skills.prepare import PrepareSkill
from app.services.openai_client import OpenAICompletionResult


def _line(line_id: str, text: str, page: int = 1, kind: str = "paragraph") -> ParsedLine:
    return ParsedLine(line_id=line_id, text=text, page=page, kind=kind)


class FakeOpenAIClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.model = "gpt-4o-mini"

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        return OpenAICompletionResult(
            content=self.payload,
            model="gpt-4o-mini",
            token_usage={
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        )


def test_pre_filter_removes_front_matter_and_clutter() -> None:
    document = ParsedDocument(
        page_count=3,
        lines=[
            _line("toc-h", "Table of Contents", page=1, kind="heading"),
            _line("toc-1", "Chapter 1 .... 3", page=1),
            _line("ch-h", "Chapter 1: Operations", page=2, kind="heading"),
            _line("ch-1", "Operations require clear intent.", page=2),
            _line("pageno", "12", page=2),
            _line("gloss-h", "Glossary of Terms", page=3, kind="heading"),
            _line("gloss-1", "Maneuver warfare: a way of thinking.", page=3),
        ],
        parser="llamaparse",
    )

    kept, report = pre_filter_lines(document)

    assert [line.line_id for line in kept] == ["ch-h", "ch-1"]
    assert "Table of Contents" in report["dropped_sections"]
    assert "Glossary of Terms" in report["dropped_sections"]
    assert report["reasons"]["page_number"] == 1


def test_pre_filter_keeps_doctrine_body() -> None:
    document = ParsedDocument(
        page_count=2,
        lines=[
            _line("dist", "DISTRIBUTION STATEMENT A: Approved for public release.", page=1),
            _line("roc-h", "Record of Changes", page=1, kind="heading"),
            _line("roc-1", "Change 1 updated paragraph 1-2.", page=1),
            _line("ch-h", "Chapter 1", page=2, kind="heading"),
            _line("ch-1", "1-1. Commanders apply judgment to the situation.", page=2),
        ],
        parser="llamaparse",
    )

    kept, report = pre_filter_lines(document)

    assert [line.line_id for line in kept] == ["ch-h", "ch-1"]
    assert "Record of Changes" in report["dropped_sections"]


def test_validate_prepared_document_fails_on_forbidden_content() -> None:
    document = ParsedDocument(
        page_count=1,
        lines=[
            _line("toc-h", "Table of Contents", page=1, kind="heading"),
            _line("toc-1", "Chapter 1 .... 3", page=1),
        ],
        parser="llamaparse",
    )

    with pytest.raises(RuntimeError, match="Prepare validation failed"):
        validate_prepared_document(document)


def test_prepare_skill_excludes_marked_lines() -> None:
    document = ParsedDocument(
        page_count=2,
        lines=[
            _line("p1-l0", "Table of Contents", page=1, kind="heading"),
            _line("p1-l1", "Chapter 1 .... 3", page=1),
            _line("p2-l0", "Chapter 1", page=2, kind="heading"),
            _line("p2-l1", "Doctrine explains intent.", page=2),
        ],
        parser="llamaparse",
    )

    skill = PrepareSkill(
        openai_client=FakeOpenAIClient(
            {
                "exclude_line_ids": [],
                "exclude_pages": [],
                "reasons": {},
            },
        ),
        batch_pages=15,
    )

    output, execution = skill.run(parsed_document=document)

    assert output.kept_line_count == 2
    assert output.excluded_line_count == 2
    assert [line.line_id for line in output.prepared_document.lines] == ["p2-l0", "p2-l1"]
    assert output.validation_report["valid"] is True
    assert execution["token_usage"]["total_tokens"] == 120


def test_prepare_skill_applies_llm_exclusions_after_pre_filter() -> None:
    document = ParsedDocument(
        page_count=2,
        lines=[
            _line("p1-l0", "Preface", page=1, kind="heading"),
            _line("p1-l1", "This manual explains doctrine.", page=1),
            _line("p2-l0", "Chapter 1", page=2, kind="heading"),
            _line("p2-l1", "Doctrine explains intent.", page=2),
        ],
        parser="llamaparse",
    )

    skill = PrepareSkill(
        openai_client=FakeOpenAIClient(
            {
                "exclude_line_ids": ["p1-l1"],
                "exclude_pages": [],
                "reasons": {"p1-l1": "preface_body"},
            },
        ),
        batch_pages=15,
    )

    output, _ = skill.run(parsed_document=document)

    assert [line.line_id for line in output.prepared_document.lines] == ["p2-l0", "p2-l1"]
