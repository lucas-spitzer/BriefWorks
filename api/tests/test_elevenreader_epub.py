import pytest

from app.mathesys.skills.eleven_reader_script import ElevenReaderScriptSkill
from app.mathesys.skills.elevenreader_epub import (
    chapter_rows_to_hydrated_chapters,
    chapter_rows_to_audio_sections,
)


def _seg(seg_id: str, kind: str, text: str, page: int = 1) -> dict:
    return {"id": seg_id, "kind": kind, "text": text, "locator": {"page": page}}


def _chapter_row(
    chapter_id: str,
    *,
    title: str,
    sequence_index: int,
    segment_ids: list[str],
) -> dict:
    return {
        "id": chapter_id,
        "title": title,
        "sequence_index": sequence_index,
        "level": 1,
        "segment_ids": segment_ids,
    }


def test_chapter_rows_to_hydrated_chapters_requires_document_chapters() -> None:
    with pytest.raises(RuntimeError, match="deconstruct-document"):
        chapter_rows_to_hydrated_chapters([], [_seg("p1", "paragraph", "Body")])


def test_build_single_epub_produces_one_volume_with_chapter_spine_items() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1: Operations", page=1),
        _seg("p1", "paragraph", "Operations require clear intent.", page=1),
        _seg("h2", "heading", "1.1 Purpose", page=1),
        _seg("p2", "paragraph", "Doctrine explains intent.", page=1),
        _seg("h3", "heading", "Chapter 2: Planning", page=2),
        _seg("p3", "paragraph", "Planning aligns resources.", page=2),
    ]
    chapter_rows = [
        _chapter_row(
            "ch-1",
            title="Chapter 1: Operations",
            sequence_index=0,
            segment_ids=["h1", "p1", "h2", "p2"],
        ),
        _chapter_row(
            "ch-2",
            title="Chapter 2: Planning",
            sequence_index=1,
            segment_ids=["h3", "p3"],
        ),
    ]

    volumes, execution = ElevenReaderScriptSkill().run(
        source_metadata={"research": {"title": "FM 3-0"}},
        segments=segments,
        wiki_entries=[],
        chapter_rows=chapter_rows,
    )

    assert len(volumes) == 1
    assert volumes[0]["part"] == 1
    assert volumes[0]["parts_total"] == 1
    assert volumes[0]["chapter_count"] == 2
    assert volumes[0]["chapter_titles"] == ["Chapter 1: Operations", "Chapter 2: Planning"]
    assert len(volumes[0]["chapters"]) == 2
    assert execution["wiki_ids_cited"] == []
    assert "elevenreader_simple_epub" in execution["transformations"]

    first_chapter_xhtml = volumes[0]["chapters"][0]["xhtml"]
    assert "<h1>Chapter 1: Operations</h1>" in first_chapter_xhtml
    assert "<h2>1.1 Purpose</h2>" in first_chapter_xhtml
    assert "<p>Operations require clear intent.</p>" in first_chapter_xhtml
    assert "<p>Doctrine explains intent.</p>" in first_chapter_xhtml

    second_chapter_xhtml = volumes[0]["chapters"][1]["xhtml"]
    assert "<h1>Chapter 2: Planning</h1>" in second_chapter_xhtml
    assert "<p>Planning aligns resources.</p>" in second_chapter_xhtml

    assert volumes[0]["epub_bytes"].startswith(b"PK")


def test_chapter_rows_to_audio_sections_preserves_subsection_headings() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1", page=1),
        _seg("p1", "paragraph", "Intro body.", page=1),
        _seg("h2", "heading", "1.1 Purpose", page=1),
        _seg("p2", "paragraph", "Purpose body.", page=1),
    ]
    chapter_rows = [
        _chapter_row(
            "ch-1",
            title="Chapter 1",
            sequence_index=0,
            segment_ids=["h1", "p1", "h2", "p2"],
        ),
    ]

    sections = chapter_rows_to_audio_sections(chapter_rows, segments)

    assert len(sections) == 1
    assert sections[0].title == "Chapter 1"
    assert len(sections[0].subsections) == 1
    assert sections[0].subsections[0].title == "1.1 Purpose"


def test_elevenreader_skill_fails_without_chapter_rows() -> None:
    segments = [_seg("p1", "paragraph", "Orphan body.", page=1)]

    with pytest.raises(RuntimeError, match="deconstruct-document"):
        ElevenReaderScriptSkill().run(
            source_metadata={"research": {"title": "FM 3-0"}},
            segments=segments,
            wiki_entries=[],
            chapter_rows=None,
        )
