from app.mathesys.chapter_grouping import group_segments_into_chapters, split_chapters_into_volumes
from app.mathesys.epub_builder import build_epub


def test_group_segments_into_chapters_splits_on_headings() -> None:
    segments = [
        {"id": "1", "kind": "heading", "text": "Chapter 1", "locator": {"page": 1}},
        {"id": "2", "kind": "paragraph", "text": "Body text.", "locator": {"page": 1}},
        {"id": "3", "kind": "heading", "text": "Chapter 2", "locator": {"page": 2}},
        {"id": "4", "kind": "paragraph", "text": "More text.", "locator": {"page": 2}},
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 2
    assert chapters[0]["title"] == "Chapter 1"
    assert chapters[1]["title"] == "Chapter 2"


def test_split_chapters_into_volumes_respects_page_limit() -> None:
    chapters = [
        {
            "title": f"Chapter {index}",
            "segments": [{"locator": {"page": index}}],
        }
        for index in range(1, 6)
    ]

    volumes = split_chapters_into_volumes(chapters, max_pages=2)

    assert len(volumes) == 3
    assert len(volumes[0]) == 2


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
