from app.intellex.llamaparse_normalizer import normalize_llamaparse_result
from app.services.llamaparse_client import LlamaParsePage, LlamaParseResult


def test_normalize_llamaparse_result_maps_headings_and_paragraphs() -> None:
    result = LlamaParseResult(
        job_id="job-1",
        pages=[
            LlamaParsePage(
                page=1,
                markdown="# Chapter 1\n\nFirst paragraph.\n\nSecond paragraph.",
            ),
            LlamaParsePage(
                page=2,
                markdown="## Section 1.1\n\nDoctrine explains intent.",
            ),
        ],
        raw_markdown="",
        api_payload={},
    )

    document = normalize_llamaparse_result(result)

    assert document.parser == "llamaparse"
    assert document.job_id == "job-1"
    assert len(document.lines) == 5
    assert document.lines[0].kind == "heading"
    assert document.lines[0].text == "Chapter 1"
    assert document.lines[0].line_id == "p1-l0"
    assert document.lines[1].kind == "paragraph"
    assert document.lines[1].text == "First paragraph."
    assert document.lines[2].text == "Second paragraph."
    assert document.lines[3].kind == "heading"
    assert document.lines[3].text == "Section 1.1"


def test_normalize_llamaparse_result_keeps_body_after_heading_in_same_block() -> None:
    result = LlamaParseResult(
        job_id="job-2",
        pages=[
            LlamaParsePage(
                page=26,
                markdown=(
                    "## THE EVOLUTION OF WAR\n"
                    "War is both timeless and ever changing.\n\n"
                    "It is important to understand which aspects of war are likely to change."
                ),
            ),
            LlamaParsePage(
                page=27,
                markdown=(
                    "## THE SCIENCE, ART, AND DYNAMIC OF WAR\n"
                    "Various aspects of war fall principally in the realm of science."
                ),
            ),
        ],
        raw_markdown="",
        api_payload={},
    )

    document = normalize_llamaparse_result(result)

    assert document.lines[0].kind == "heading"
    assert document.lines[0].text == "THE EVOLUTION OF WAR"
    assert document.lines[1].kind == "paragraph"
    assert "War is both timeless" in document.lines[1].text
    assert document.lines[2].kind == "paragraph"
    assert "It is important to understand" in document.lines[2].text
    assert document.lines[3].kind == "heading"
    assert document.lines[3].text == "THE SCIENCE, ART, AND DYNAMIC OF WAR"
    assert document.lines[4].kind == "paragraph"
    assert "Various aspects of war" in document.lines[4].text
