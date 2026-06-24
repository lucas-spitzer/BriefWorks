# Quiz Question Generation Skill

## Purpose

Generate quiz questions that measure whether a learner has met the **learning
objectives** for a chapter. Questions test **Understand**-level comprehension and
must be grounded in the provided concept cards and evidence segments.

## Objective-driven generation

Questions are planned from learning objectives, **not** one-per-concept:

- Write **exactly one question per learning objective** provided. Each question
  must assess whether the learner has achieved that objective.
- Ground the question in the concepts named by the objective and their evidence
  segments. Pull supporting detail from the other concepts in the batch only
  when it strengthens the question.
- If **no objectives** are provided for the batch, write up to **3** questions
  covering the most important concepts in the batch (essential first).

Do not pad the set to cover every concept. A focused question that probes an
objective is worth more than broad coverage.

## Grounding Rules

- Every question must cite `wiki_ids_cited` and `source_chunk_ids` from the batch.
- Use `preferred_label` verbatim in question stems when referencing a concept.
- Correct answers must be derivable from the provided definitions and evidence.
- Do not invent concepts or facts outside the batch.

## Subtypes

- `multiple_choice` (preferred): 4 choices, one correct answer
- `true_false_correction`: statement + correction if false
- `multiple_select`: multiple correct answers (semicolon-separated in correct_answer)

## Distractor Engineering

- Distractors must be plausible but clearly wrong given the source.
- Avoid "all of the above" / "none of the above" unless evidence supports it.
- Distractors should reflect common misconceptions, not random unrelated terms.
- Keep choices parallel in length and grammatical structure.
- `correct_answer` must match one of the `choices` **verbatim** (no "A)" labels).

## Draft Checklist

1. One question per objective (or up to 3 concept questions when no objectives).
2. Tag each question with the `objective_id` it assesses when one applies.
3. Include an explanation citing why the correct answer is right.
4. Calibrate difficulty: easy = direct recall, medium = application, hard = comparison.

## Critique Checklist

1. Does each question actually assess its objective (not just name a concept)?
2. Is the correct answer unambiguously supported by evidence?
3. Are distractors plausible but definitively wrong?
4. Does `correct_answer` appear verbatim among `choices`?

## Output Schema

```json
{
  "items": [
    {
      "item_id": "uuid",
      "type": "quiz",
      "subtype": "multiple_choice",
      "difficulty": "easy|medium|hard",
      "objective_id": "objective this question assesses (optional)",
      "wiki_ids_cited": ["wiki-id"],
      "source_chunk_ids": ["segment-id"],
      "question": "question text",
      "choices": ["A", "B", "C", "D"],
      "correct_answer": "exact text of the correct choice",
      "explanation": "why correct"
    }
  ]
}
```
