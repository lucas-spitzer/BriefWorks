from app.intellex.heading_classification import (
    is_chapter_boundary_heading,
    is_doctrinal_subsection_heading,
    is_toc_outline_line,
    parse_chapter_boundary_number,
)
from app.mathesys.chapter_grouping import (
    collapse_chapter_rows_for_spine,
    group_segments_into_chapters,
)


def test_parse_chapter_boundary_number() -> None:
    assert parse_chapter_boundary_number("Chapter 2") == 2
    assert parse_chapter_boundary_number("Chapter 2: The Theory of War") == 2
    assert parse_chapter_boundary_number("WAR DEFINED") is None


def test_is_chapter_boundary_heading() -> None:
    assert is_chapter_boundary_heading("Chapter 1")
    assert not is_chapter_boundary_heading("Chapter 1.")
    assert is_chapter_boundary_heading("Chapter 1: The Nature of War")
    assert is_chapter_boundary_heading("Part II")
    assert not is_chapter_boundary_heading("WAR DEFINED")
    assert not is_chapter_boundary_heading("The Nature of War")
    assert not is_chapter_boundary_heading("MCDP 1")


def test_is_toc_outline_line_matches_topic_lists_not_prose() -> None:
    assert is_toc_outline_line("War Defined—Friction——Uncertainty-—Fluidity—")
    assert not is_toc_outline_line(
        "large—even decisive—effects. While dependent on the laws",
    )


def test_is_doctrinal_subsection_heading() -> None:
    assert is_doctrinal_subsection_heading("THE EVOLUTION OF WAR")
    assert is_doctrinal_subsection_heading("Tm EVOLUTION OF WAR")
    assert not is_doctrinal_subsection_heading("Chapter 2")


def test_group_segments_splits_only_on_chapter_boundaries() -> None:
    segments = [
        {"id": "h1", "kind": "heading", "text": "Chapter 1", "locator": {"page": 1}},
        {"id": "h2", "kind": "heading", "text": "The Nature of War", "locator": {"page": 1}},
        {"id": "h3", "kind": "heading", "text": "WAR DEFINED", "locator": {"page": 1}},
        {"id": "p1", "kind": "paragraph", "text": "War is violent.", "locator": {"page": 1}},
        {"id": "h4", "kind": "heading", "text": "Chapter 2", "locator": {"page": 2}},
        {"id": "p2", "kind": "paragraph", "text": "Theory follows.", "locator": {"page": 2}},
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 2
    assert chapters[0]["title"] == "Chapter 1 — The Nature of War"
    assert [segment["id"] for segment in chapters[0]["segments"]] == [
        "h1",
        "h2",
        "h3",
        "p1",
    ]


def test_group_segments_splits_paragraph_leading_with_chapter_boundary() -> None:
    """LlamaParse often embeds 'Chapter 2' inside a large paragraph block."""
    segments = [
        {"id": "h1", "kind": "heading", "text": "Chapter 1", "locator": {"page": 10}},
        {"id": "h1t", "kind": "heading", "text": "The Nature of War", "locator": {"page": 10}},
        {"id": "p0", "kind": "paragraph", "text": "Chapter 1 closing text.", "locator": {"page": 29}},
        {
            "id": "p1",
            "kind": "paragraph",
            "text": "Chapter 2\nThe Theory of War\n\nWar is policy by other means.",
            "locator": {"page": 30},
        },
        {"id": "h3", "kind": "heading", "text": "Chapter 3", "locator": {"page": 60}},
        {"id": "p3", "kind": "paragraph", "text": "Prepare the force.", "locator": {"page": 60}},
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 3
    assert chapters[0]["title"] == "Chapter 1 — The Nature of War"
    assert chapters[0]["segments"][-1]["text"] == "Chapter 1 closing text."
    assert chapters[1]["title"] == "Chapter 2 — The Theory of War"
    assert chapters[1]["segments"][0]["text"] == "Chapter 2"
    assert "War is policy by other means." in chapters[1]["segments"][-1]["text"]
    assert chapters[2]["title"] == "Chapter 3"


def test_group_segments_splits_mid_paragraph_chapter_boundary() -> None:
    """LlamaParse may append the next chapter title after the prior chapter body."""
    segments = [
        {"id": "h1", "kind": "heading", "text": "Chapter 1", "locator": {"page": 10}},
        {"id": "h1t", "kind": "heading", "text": "The Nature of War", "locator": {"page": 10}},
        {
            "id": "p1",
            "kind": "paragraph",
            "text": (
                "Chapter 1 closing paragraph.\n"
                "Chapter 2\n"
                '"The political object is the goal."\n\n'
                "Having arrived at a common view of the nature of war, we proceed."
            ),
            "locator": {"page": 30},
        },
        {"id": "h3", "kind": "heading", "text": "Chapter 3", "locator": {"page": 60}},
        {"id": "p3", "kind": "paragraph", "text": "Prepare the force.", "locator": {"page": 60}},
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 3
    assert chapters[0]["title"] == "Chapter 1 — The Nature of War"
    assert chapters[0]["segments"][-1]["text"] == "Chapter 1 closing paragraph."
    assert chapters[1]["title"] == "Chapter 2"
    assert chapters[1]["segments"][0]["text"] == "Chapter 2"
    assert "Having arrived at a common view" in chapters[1]["segments"][-1]["text"]
    assert chapters[2]["title"] == "Chapter 3"


def test_group_segments_ignores_out_of_sequence_chapter_headings() -> None:
    segments = [
        {"id": "h1", "kind": "heading", "text": "Chapter 1", "locator": {"page": 10}},
        {"id": "p1", "kind": "paragraph", "text": "Nature of war body.", "locator": {"page": 11}},
        {"id": "h3", "kind": "heading", "text": "Chapter 3", "locator": {"page": 8}},
        {"id": "p3", "kind": "paragraph", "text": "TOC spillover.", "locator": {"page": 8}},
        {"id": "h2", "kind": "heading", "text": "Chapter 2", "locator": {"page": 30}},
        {"id": "h2t", "kind": "heading", "text": "The Theory of War", "locator": {"page": 30}},
        {"id": "p2", "kind": "paragraph", "text": "Theory body.", "locator": {"page": 31}},
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 2
    assert chapters[0]["title"] == "Chapter 1"
    assert chapters[1]["title"] == "Chapter 2 — The Theory of War"
    assert any(segment["id"] == "h3" for segment in chapters[0]["segments"])


def test_collapse_chapter_rows_for_spine_merges_subsections() -> None:
    rows = [
        {
            "id": "ch-1",
            "sequence_index": 0,
            "title": "Chapter 1",
            "level": 1,
            "segment_ids": ["a"],
        },
        {
            "id": "ch-1a",
            "sequence_index": 1,
            "title": "WAR DEFINED",
            "level": 1,
            "segment_ids": ["b", "c"],
        },
        {
            "id": "ch-2",
            "sequence_index": 2,
            "title": "Chapter 2",
            "level": 1,
            "segment_ids": ["d"],
        },
    ]

    collapsed = collapse_chapter_rows_for_spine(rows)

    assert len(collapsed) == 2
    assert collapsed[0]["segment_ids"] == ["a", "b", "c"]
    assert collapsed[1]["segment_ids"] == ["d"]
