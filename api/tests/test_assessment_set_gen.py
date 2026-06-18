from typing import Any

from app.qngen.canonical_context import ConceptCard
from app.qngen.skills.assessment_set_gen import AssessmentSetGenSkill
from app.services.openai_client import OpenAICompletionResult


class FakeOpenAIClient:
    model = "gpt-4o"

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_prompt: str, model: str | None = None):
        del system_prompt, user_prompt, model
        content = self.responses[self.calls]
        self.calls += 1
        return OpenAICompletionResult(
            content=content,
            model=self.model,
            token_usage={"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        )


def _concept(wiki_id: str, label: str) -> ConceptCard:
    return ConceptCard(
        wiki_id=wiki_id,
        preferred_label=label,
        definition=f"Definition for {label}",
        importance="essential",
        evidence_segment_ids=["seg-1"],
        evidence_segments=[
            {"segment_id": "seg-1", "kind": "paragraph", "text": "Evidence text.", "page": 1},
        ],
    )


def test_assessment_set_gen_merges_batches_and_filters_types() -> None:
    skill = AssessmentSetGenSkill(
        openai_client=FakeOpenAIClient(
            [
                {
                    "items": [
                        {
                            "item_id": "fc-1",
                            "type": "flashcard",
                            "subtype": "term_definition",
                            "difficulty": "easy",
                            "front": "What is Alpha?",
                            "back": "Definition for Alpha",
                            "wiki_ids_cited": ["wiki-1"],
                            "source_chunk_ids": ["seg-1"],
                        },
                        {
                            "item_id": "quiz-1",
                            "type": "quiz",
                            "subtype": "multiple_choice",
                            "difficulty": "medium",
                            "question": "Alpha question",
                            "choices": ["A", "B"],
                            "correct_answer": "A",
                            "wiki_ids_cited": ["wiki-1"],
                            "source_chunk_ids": ["seg-1"],
                        },
                        {
                            "item_id": "scenario-1",
                            "type": "scenario",
                            "subtype": "decision_prompt",
                            "difficulty": "hard",
                            "task": "Apply Alpha",
                            "wiki_ids_cited": ["wiki-1"],
                            "source_chunk_ids": ["seg-1"],
                        },
                    ],
                },
                {
                    "items": [
                        {
                            "item_id": "fc-2",
                            "type": "flashcard",
                            "subtype": "term_definition",
                            "difficulty": "easy",
                            "front": "What is Beta?",
                            "back": "Definition for Beta",
                            "wiki_ids_cited": ["wiki-2"],
                            "source_chunk_ids": ["seg-1"],
                        },
                    ],
                },
            ],
        ),
    )

    output, execution = skill.run(
        source_metadata={"research": {"title": "Doctrine"}},
        concept_batches=[[_concept("wiki-1", "Alpha")], [_concept("wiki-2", "Beta")]],
        assessment_types=["flashcards", "quizzes"],
    )

    assert execution["batch_count"] == 2
    assert len(output.items) == 3
    assert {item["type"] for item in output.items} == {"flashcard", "quiz"}
