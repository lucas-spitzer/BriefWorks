import pytest

from app.intellex.skills.deconstructor_models import DocumentChapter, validate_chapter_segmentation
from app.intellex.skills.document_deconstructor import DocumentDeconstructorSkill
from app.mathesys.chapter_grouping import group_segments_into_chapters, hydrate_chapters_from_rows
from app.services.openai_client import OpenAICompletionResult


def _seg(seg_id: str, kind: str, text: str, page: int = 1) -> dict:
    return {"id": seg_id, "kind": kind, "text": text, "locator": {"page": page}}


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


def test_group_segments_into_chapters_doctrine_fixture() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1: Operations", page=1),
        _seg("p1", "paragraph", "Operations require clear intent.", page=1),
        _seg("h2", "heading", "Section 1-1. Command", page=2),
        _seg("p2", "paragraph", "Commanders apply judgment.", page=2),
    ]

    chapters = group_segments_into_chapters(segments)

    assert len(chapters) == 2
    assert chapters[0]["title"] == "Chapter 1: Operations"
    assert [segment["id"] for segment in chapters[0]["segments"]] == ["h1", "p1"]


def test_validate_chapter_segmentation_requires_full_coverage() -> None:
    chapters = [
        DocumentChapter(sequence_index=0, title="Chapter 1", segment_ids=["a"]),
    ]

    with pytest.raises(RuntimeError, match="does not cover all segments"):
        validate_chapter_segmentation(chapters, all_segment_ids={"a", "b"})


def test_document_deconstructor_skill_uses_llm_refinement() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1", page=1),
        _seg("p1", "paragraph", "Body one.", page=1),
        _seg("h2", "heading", "Chapter 2", page=2),
        _seg("p2", "paragraph", "Body two.", page=2),
    ]

    skill = DocumentDeconstructorSkill(
        openai_client=FakeOpenAIClient(
            {
                "chapters": [
                    {
                        "sequence_index": 0,
                        "title": "Chapter 1",
                        "level": 1,
                        "segment_ids": ["h1", "p1"],
                    },
                    {
                        "sequence_index": 1,
                        "title": "Chapter 2",
                        "level": 1,
                        "segment_ids": ["h2", "p2"],
                    },
                ],
            },
        ),
    )

    output, execution = skill.run(source_metadata={}, segments=segments)

    assert len(output.chapters) == 2
    assert output.chapters[0].segment_ids == ["h1", "p1"]
    assert execution["baseline_chapter_count"] == 2


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
