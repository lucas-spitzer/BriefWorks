import pytest

from app.intellex.stages.concept_models import DeconstructedConcept
from app.intellex.stages.extract_chapter_knowledge import (
    ExtractChapterKnowledgeStage,
    merge_knowledge_items,
)
from app.intellex.stages.wiki_promotion import build_evidence_records, promote_concepts_to_wiki
from app.services.llm.base import LLMCompletionResult


def _seg(seg_id: str, kind: str, text: str, page: int = 1) -> dict:
    return {"id": seg_id, "kind": kind, "text": text, "locator": {"page": page}}


class FakeLLMClient:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)
        self.provider = "anthropic"
        self.model = "claude-sonnet-4-6"
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        payload = self.payloads[self.calls]
        self.calls += 1
        return LLMCompletionResult(
            content=payload,
            model=self.model,
            provider=self.provider,
            token_usage={
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        )


def test_merge_knowledge_items_unions_evidence_and_aliases() -> None:
    items = [
        DeconstructedConcept(
            term_label="Maneuver warfare",
            definition="A way of thinking about war.",
            entry_kind="concept",
            aliases=["maneuverist approach"],
            evidence_segment_ids=["a"],
            importance="supporting",
        ),
        DeconstructedConcept(
            term_label="Maneuver warfare",
            definition="A way of thinking about war.",
            entry_kind="concept",
            aliases=["warfighting approach"],
            evidence_segment_ids=["b"],
            importance="essential",
        ),
    ]

    merged = merge_knowledge_items(items)

    assert len(merged) == 1
    assert merged[0].importance == "essential"
    assert set(merged[0].evidence_segment_ids) == {"a", "b"}


def test_merge_knowledge_items_keeps_different_entry_kinds_separate() -> None:
    items = [
        DeconstructedConcept(
            term_label="Combined arms",
            definition="Synchronizing capabilities.",
            entry_kind="concept",
            evidence_segment_ids=["a"],
        ),
        DeconstructedConcept(
            term_label="Combined arms",
            definition="Leaders must integrate fires and maneuver.",
            entry_kind="insight",
            evidence_segment_ids=["b"],
        ),
    ]

    merged = merge_knowledge_items(items)

    assert len(merged) == 2
    kinds = {item.entry_kind for item in merged}
    assert kinds == {"concept", "insight"}


def test_extract_stage_runs_objectives_concepts_and_consolidation() -> None:
    segments = [
        _seg("h1", "heading", "Chapter 1", page=1),
        _seg("p1", "paragraph", "Doctrine explains intent.", page=1),
        _seg("h2", "heading", "Chapter 2", page=2),
        _seg("p2", "paragraph", "Commanders apply judgment.", page=2),
    ]
    chapter_rows = [
        {
            "id": "ch-1",
            "title": "Chapter 1",
            "sequence_index": 0,
            "level": 1,
            "segment_ids": ["h1", "p1"],
        },
        {
            "id": "ch-2",
            "title": "Chapter 2",
            "sequence_index": 1,
            "level": 1,
            "segment_ids": ["h2", "p2"],
        },
    ]
    client = FakeLLMClient(
        [
            {"objectives": [{"objective_id": "ch1-obj-1", "statement": "Understand doctrine", "bloom_level": "understand", "concept_labels": []}]},
            {
                "items": [
                    {
                        "entry_kind": "concept",
                        "term_label": "Doctrine",
                        "definition": "Guides decisions.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "essential",
                        "evidence_segment_ids": ["p1"],
                        "evidence_quotes": [{"segment_id": "p1", "quote": "Doctrine explains intent."}],
                        "objective_labels": ["ch1-obj-1"],
                        "confidence": 0.9,
                    },
                ],
            },
            {"objectives": [{"objective_id": "ch2-obj-1", "statement": "Apply judgment", "bloom_level": "apply", "concept_labels": []}]},
            {
                "items": [
                    {
                        "entry_kind": "insight",
                        "term_label": "Judgment under uncertainty",
                        "definition": "Commanders adapt to context.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "supporting",
                        "evidence_segment_ids": ["p2"],
                        "evidence_quotes": [{"segment_id": "p2", "quote": "Commanders apply judgment."}],
                        "objective_labels": ["ch2-obj-1"],
                        "confidence": 0.8,
                    },
                ],
            },
            {
                "items": [
                    {
                        "entry_kind": "concept",
                        "term_label": "Doctrine",
                        "definition": "Guides decisions.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "essential",
                        "evidence_segment_ids": ["p1"],
                        "evidence_quotes": [{"segment_id": "p1", "quote": "Doctrine explains intent."}],
                        "objective_labels": ["ch1-obj-1"],
                        "confidence": 0.9,
                    },
                    {
                        "entry_kind": "insight",
                        "term_label": "Judgment under uncertainty",
                        "definition": "Commanders adapt to context.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "supporting",
                        "evidence_segment_ids": ["p2"],
                        "evidence_quotes": [{"segment_id": "p2", "quote": "Commanders apply judgment."}],
                        "objective_labels": ["ch2-obj-1"],
                        "confidence": 0.8,
                    },
                ],
            },
        ],
    )

    stage = ExtractChapterKnowledgeStage(llm_client=client)
    output, execution = stage.run(
        source_metadata={},
        chapter_rows=chapter_rows,
        segments=segments,
        existing_labels=[],
    )

    assert client.calls == 5
    assert len(output.chapters) == 2
    assert len(output.items) == 2
    assert len(output.learning_objectives) == 2
    assert execution["chapter_count"] == 2
    assert execution["provider"] == "anthropic"


def test_build_evidence_records_includes_quotes() -> None:
    concept = DeconstructedConcept(
        term_label="METT-TC",
        definition="Mission, Enemy, Terrain, Troops, Time, Civilians.",
        entry_kind="term",
        importance="essential",
        evidence_segment_ids=["seg-1"],
        evidence_quotes=[{"segment_id": "seg-1", "quote": "METT-TC guides analysis."}],
    )
    segment_index = {
        "seg-1": {
            "id": "seg-1",
            "kind": "paragraph",
            "text": "METT-TC guides analysis.",
            "locator": {"page": 2},
        },
    }

    evidence = build_evidence_records(
        source_id="src-1",
        concept=concept,
        segment_index=segment_index,
    )

    assert evidence[0]["quote"] == "METT-TC guides analysis."


def test_promote_concepts_to_wiki_sets_entry_kind() -> None:
    concept = DeconstructedConcept(
        term_label="METT-TC",
        definition="Mission, Enemy, Terrain, Troops, Time, Civilians.",
        entry_kind="term",
        importance="essential",
        evidence_segment_ids=["seg-1"],
        chapter_id="ch-1",
        chapter_sequence_index=0,
    )
    segment_index = {
        "seg-1": {
            "id": "seg-1",
            "kind": "paragraph",
            "text": "METT-TC guides analysis.",
            "locator": {"page": 2},
        },
    }

    inserts, updates, disputes = promote_concepts_to_wiki(
        workspace_id="ws-1",
        source_id="src-1",
        stage_run_id="run-1",
        stage_id="extract-knowledge",
        stage_version="2.0",
        concepts=[concept],
        segment_index=segment_index,
        existing_entries=[],
    )

    assert not updates
    assert not disputes
    assert inserts[0]["entry_kind"] == "term"
    assert inserts[0]["origin"]["chapter_id"] == "ch-1"


def test_format_chapter_segments_for_llm_raises_over_budget() -> None:
    from app.intellex.chapter_formatting import format_chapter_segments_for_llm

    huge_segment = _seg("h1", "heading", "x" * 100_000, page=1)

    with pytest.raises(RuntimeError, match="Segment exceeds extract budget"):
        format_chapter_segments_for_llm([huge_segment], max_chars=1000)


def test_batch_chapter_segments_for_llm_splits_large_chapters() -> None:
    from app.intellex.chapter_formatting import batch_chapter_segments_for_llm

    segments = [
        _seg("p1", "paragraph", "a" * 600, page=1),
        _seg("p2", "paragraph", "b" * 600, page=1),
    ]

    batches = batch_chapter_segments_for_llm(segments, max_chars=1000)

    assert len(batches) == 2
    assert '"segment_id": "p1"' in batches[0][0]
    assert '"segment_id": "p2"' in batches[1][0]


def test_extract_stage_batches_oversized_chapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXTRACT_CHAPTER_MAX_CHARS", "1000")

    segments = [
        _seg("p1", "paragraph", "a" * 600, page=1),
        _seg("p2", "paragraph", "b" * 600, page=2),
    ]
    chapter_rows = [
        {
            "id": "ch-1",
            "title": "Chapter 1",
            "sequence_index": 0,
            "level": 1,
            "segment_ids": ["p1", "p2"],
        },
    ]

    client = FakeLLMClient(
        [
            {"objectives": [{"objective_id": "obj-1", "statement": "Learn", "bloom_level": "remember", "concept_labels": []}]},
            {
                "items": [
                    {
                        "entry_kind": "concept",
                        "term_label": "Alpha",
                        "definition": "First batch concept.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "essential",
                        "evidence_segment_ids": ["p1"],
                        "evidence_quotes": [],
                        "objective_labels": [],
                        "confidence": 0.9,
                    },
                ],
            },
            {
                "items": [
                    {
                        "entry_kind": "concept",
                        "term_label": "Beta",
                        "definition": "Second batch concept.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "supporting",
                        "evidence_segment_ids": ["p2"],
                        "evidence_quotes": [],
                        "objective_labels": [],
                        "confidence": 0.8,
                    },
                ],
            },
            {
                "items": [
                    {
                        "entry_kind": "concept",
                        "term_label": "Alpha",
                        "definition": "First batch concept.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "essential",
                        "evidence_segment_ids": ["p1"],
                        "evidence_quotes": [],
                        "objective_labels": [],
                        "confidence": 0.9,
                    },
                    {
                        "entry_kind": "concept",
                        "term_label": "Beta",
                        "definition": "Second batch concept.",
                        "aliases": [],
                        "prerequisite_labels": [],
                        "pronunciation": None,
                        "importance": "supporting",
                        "evidence_segment_ids": ["p2"],
                        "evidence_quotes": [],
                        "objective_labels": [],
                        "confidence": 0.8,
                    },
                ],
            },
        ],
    )

    stage = ExtractChapterKnowledgeStage(llm_client=client)
    output, execution = stage.run(
        source_metadata={"research": {"title": "Doctrine"}},
        chapter_rows=chapter_rows,
        segments=segments,
    )

    assert client.calls == 4
    assert len(output.items) == 2
    assert {item.term_label for item in output.items} == {"Alpha", "Beta"}
    assert execution["token_usage"]["total_tokens"] == 480
