from app.intellex.heading_classification import (
    is_chapter_boundary_heading,
    is_doctrinal_subsection_heading,
    is_toc_outline_line,
    parse_chapter_boundary_number,
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
