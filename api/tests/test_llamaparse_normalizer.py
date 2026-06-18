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
