from app.mathesys.epub_builder import build_epub


def test_build_epub_returns_bytes() -> None:
    epub_bytes = build_epub(
        title="Warfighting",
        author="US Marine Corps",
        identifier="MCDP 1",
        language="en",
        publication_date="1997-06-20",
        chapters=[
            {
                "title": "Chapter 1",
                "sections": [
                    {
                        "heading": "Purpose",
                        "heading_level": 2,
                        "paragraphs": ["This publication describes the philosophy of warfighting."],
                    },
                ],
            },
        ],
    )

    assert epub_bytes.startswith(b"PK")


def test_build_epub_accepts_prebuilt_xhtml_body() -> None:
    epub_bytes = build_epub(
        title="Warfighting",
        author="US Marine Corps",
        identifier="MCDP 1",
        language="en",
        publication_date=None,
        chapters=[
            {
                "title": "Chapter 1",
                "xhtml_body": "<h1>Chapter 1</h1><p>Opening paragraph.</p>",
            },
        ],
    )

    assert epub_bytes.startswith(b"PK")
