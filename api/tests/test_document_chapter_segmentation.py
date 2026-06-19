import pytest

from app.intellex.stages.deconstructor_models import DocumentChapter, validate_chapter_segmentation
from app.intellex.stages.document_deconstructor import DocumentDeconstructorStage
from app.mathesys.chapter_grouping import group_segments_into_chapters, hydrate_chapters_from_rows


def _seg(seg_id: str, kind: str, text: str, page: int = 1) -> dict:
    return {"id": seg_id, "kind": kind, "text": text, "locator": {"page": page}}


def test_group_segments_into_chapters_doctrine_fixture() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1: Operations", page=1),
        _seg("p1", "paragraph", "Operations require clear intent.", page=1),
        _seg("h2", "heading", "Section 1-1. Command", page=2),
        _seg("p2", "paragraph", "Commanders apply judgment.", page=2),
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 1
    assert chapters[0]["title"] == "Chapter 1: Operations"
    assert [segment["id"] for segment in chapters[0]["segments"]] == [
        "h1",
        "p1",
        "h2",
        "p2",
    ]


def test_validate_chapter_segmentation_requires_full_coverage() -> None:
    chapters = [
        DocumentChapter(sequence_index=0, title="Chapter 1", segment_ids=["a"]),
    ]

    with pytest.raises(RuntimeError, match="does not cover all segments"):
        validate_chapter_segmentation(chapters, all_segment_ids={"a", "b"})


def test_document_deconstructor_stage_uses_deterministic_chapter_boundaries() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1", page=1),
        _seg("h1b", "heading", "WAR DEFINED", page=1),
        _seg("p1", "paragraph", "Body one.", page=1),
        _seg("h2", "heading", "Chapter 2", page=2),
        _seg("p2", "paragraph", "Body two.", page=2),
    ]

    stage = DocumentDeconstructorStage()
    output, execution = stage.run(source_metadata={}, segments=segments)

    assert len(output.chapters) == 2
    assert output.chapters[0].title == "Chapter 1 — WAR DEFINED"
    assert output.chapters[0].segment_ids == ["h1", "h1b", "p1"]
    assert output.chapters[1].segment_ids == ["h2", "p2"]
    assert execution["model"] == "deterministic-chapter-boundaries"
    assert execution["token_usage"] == {}


def test_hydrate_chapters_from_rows() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1", page=1),
        _seg("p1", "paragraph", "Body one.", page=1),
    ]
    segment_index = {segment["id"]: segment for segment in segments}
    rows = [
        {
            "title": "Chapter 1",
            "segment_ids": ["h1", "p1"],
        },
    ]

    chapters = hydrate_chapters_from_rows(rows, segment_index)

    assert len(chapters) == 1
    assert chapters[0]["title"] == "Chapter 1"
    assert [segment["id"] for segment in chapters[0]["segments"]] == ["h1", "p1"]
