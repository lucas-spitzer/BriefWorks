from app.services.llamaparse_client import LlamaParseClient, LlamaParseError, _response_json


def test_extract_pages_from_markdown_payload() -> None:
    client = LlamaParseClient(api_key="test-key")
    payload = {
        "markdown": {
            "pages": [
                {"page": 1, "markdown": "# Title"},
                {"page": 2, "markdown": "Body text"},
            ],
        },
    }

    pages = client._extract_pages(payload)

    assert len(pages) == 2
    assert pages[0].page == 1
    assert pages[0].markdown == "# Title"
    assert pages[1].page == 2


def test_extract_pages_from_markdown_full_fallback() -> None:
    client = LlamaParseClient(api_key="test-key")
    payload = {"markdown_full": "# Full doc\n\nParagraph."}

    pages = client._extract_pages(payload)

    assert len(pages) == 1
    assert pages[0].page == 1
    assert "Full doc" in pages[0].markdown


def test_response_json_raises_on_empty_body() -> None:
    import httpx

    response = httpx.Response(307, content=b"")

    try:
        _response_json(response)
        assert False, "expected LlamaParseError"
    except LlamaParseError as exc:
        assert "non-JSON response (307)" in str(exc)
