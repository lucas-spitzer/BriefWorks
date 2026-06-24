from typing import Any

from app.qngen.canonical_context import ConceptCard
from app.qngen.skills.shared.orchestrator import run_skill_batch
from app.services.llm.base import LLMCompletionResult


class FakeClient:
    model = "gpt-4o"

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        del system_prompt, user_prompt, model
        content = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return LLMCompletionResult(
            content=content,
            model=self.model,
            provider="fake",
            token_usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        )


def _supporting_concept() -> ConceptCard:
    # ``supporting`` importance keeps the critique pass off so the test isolates
    # the grounding repair loop.
    return ConceptCard(
        wiki_id="wiki-1",
        preferred_label="Tempo",
        definition="Speed over time.",
        importance="supporting",
        evidence_segment_ids=["seg-1"],
        evidence_segments=[
            {"segment_id": "seg-1", "kind": "paragraph", "text": "Tempo text.", "page": 1},
        ],
    )


def test_repair_loop_regrounds_invalid_citations() -> None:
    draft = {
        "items": [
            {
                "item_id": "q1",
                "subtype": "multiple_choice",
                "question": "What is tempo?",
                "choices": ["Speed over time.", "A map."],
                "correct_answer": "Speed over time.",
                "wiki_ids_cited": ["wiki-1"],
                "source_chunk_ids": ["seg-bad"],
            },
        ],
    }
    repaired = {
        "items": [
            {
                "item_id": "q1",
                "subtype": "multiple_choice",
                "question": "What is tempo?",
                "choices": ["Speed over time.", "A map."],
                "correct_answer": "Speed over time.",
                "wiki_ids_cited": ["wiki-1"],
                "source_chunk_ids": ["seg-1"],
            },
        ],
    }

    draft_client = FakeClient([draft, repaired])

    items, _execution = run_skill_batch(
        skill_name="questions",
        artifact_type="quiz",
        source_metadata={"research": {"title": "Doctrine"}},
        concepts=[_supporting_concept()],
        learning_objectives=[],
        draft_client=draft_client,
        critique_client=FakeClient([{"items": []}]),
    )

    assert len(items) == 1
    assert items[0]["source_chunk_ids"] == ["seg-1"]
    # One draft call + at least one repair call.
    assert draft_client.calls >= 2
