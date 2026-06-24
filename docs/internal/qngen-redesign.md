# QnGen Redesign Plan

## Background: why the current output is inconsistent

The current QnGen flow is **concept fan-out**: every canonical wiki concept with
evidence becomes one assessment item. Each `SKILL.md` literally says "one item per
concept in the batch." So counts are emergent, not chosen:

- **100 flashcards** — ~100 canonical concepts, deduped by `wiki_id`
  (`prefer_term_definition`), capped at 2/concept by the validator.
- **100 scenarios** — the "essential only" gate barely filters because most
  concepts are tagged `essential`.
- **6 questions** — a bug, not a choice. The generator produced ~100 quizzes, but
  the validator silently culled almost all of them. In
  `qngen/validators.py`, the answer-in-choices check only runs for subtypes
  `{multiple_choice, true_false_correction}`. The 6 survivors are all plain
  `true_false`, a subtype that bypasses validation. Every multiple-choice question
  whose `correct_answer` didn't string-match a choice was dropped.

Two further defects:

- **Flashcard case duplicates** — dedup is by `wiki_id` only, so two canonical
  entries that differ only in casing (`Enemy system` vs `enemy system`) both
  survive as separate cards.
- **Silent drops** — validation discards malformed items instead of repairing
  them, which is the root cause of the 6-vs-100 inconsistency.

## Design principles

1. **Blueprint-driven, not concept fan-out.** Counts are decided in an explicit
   planning step, never as an emergent side effect of `len(concepts)`.
2. **Quality-driven counts within guardrails.** `importance` sets a floor; a
   curation step lets the model pick *which* concepts deserve items, bounded by
   per-chapter min/max bands so output scales with content richness but never
   collapses or explodes.
3. **Repair, don't drop.** Validation runs as a bounded generate→check→revise
   loop (the agentic *pattern*, built on the existing `LLMClient` — no Agent SDK
   dependency).
4. **Reuse intellex chapters.** Chapter/objective structure already exists
   upstream; surface it to qngen rather than re-deriving.

---

## Phase 0 — Plumbing: expose chapter structure to QnGen

**Problem:** `source_metadata["extract"]["learning_objectives"]` is a flattened
list (`worker/stage_executor.py`); the chapter→objective→concept mapping is lost.

**Changes:**

- Persist a structured `source_metadata["extract"]["chapters"]` block: each entry
  `{chapter_id, chapter_title, sequence_index, objectives: [...], segment_ids: [...]}`.
  Objectives already carry `concept_labels` (`intellex/stages/concept_models.py`).
- Add `build_chapter_blueprint()` in `qngen/canonical_context.py` joining this
  with `build_source_concepts` — concepts grouped under chapters via
  `evidence_segment_ids ∩ chapter.segment_ids`, under objectives via
  `concept_labels`.

Additive, backward-compatible. Prerequisite for Phases 2–4.

---

## Phase 1 — Bug fixes + bounded repair loop *(ships standalone, do first)*

1. **Validator `true_false` leak** (`qngen/validators.py`) — validate all
   choice-based subtypes, not just `{multiple_choice, true_false_correction}`.
2. **Repair instead of drop** — wrap generation in a bounded loop
   (`max_repair_turns ≈ 3`):
   ```
   propose → validate → if failures: feed specific errors back → revise
           → recheck → repeat → drop only what's still invalid
   ```
   Built with the existing `LLMClient.complete_json` in a plain loop. Cheap
   coercions first (trim `"B) "` prefixes, case-insensitive match), then model
   revision for the rest.
3. **Flashcard case-duplicate dedup** (`qngen/skills/flashcards/helpers.py`) —
   dedupe on `casefold(preferred_label)`, not `wiki_id`; on collision keep the
   best-grounded `term_definition` and run a short definition-polish pass.

**Verifiable outcome:** questions stop collapsing to 6; flashcard upper/lower
duplicates disappear.

---

## Phase 2 — Questions: objective/subsection-driven

- **Blueprint (deterministic):** per chapter → its ~3 objectives; per subsection
  → 1 question slot tagged to an objective.
- **Curate:** model confirms/adjusts slots within band (default: 3
  objective-questions/chapter + 1/subsection).
- **Generate:** one call per slot, given objective + subsection evidence. Rewrite
  `questions/SKILL.md`: drop "one quiz per concept"; assess *the objective*.
  Default `multiple_choice`.
- **Validate/Repair:** Phase 1 loop.

Count = predictable function of learning structure, not corpus size.

---

## Phase 3 — Scenarios: tactical decision games

- **Blueprint:** one TDG candidate per chapter / high-salience objective cluster —
  **not** per essential concept.
- **Curate:** model selects decision-worthy themes within band **1–3 per
  chapter** (kills the 100-scenario flood).
- **Generate:** richer multi-part TDG
  (`situation → task → expected_response_elements → rubric`). Update
  `scenarios/SKILL.md` to frame output explicitly as a tactical decision game
  with a clear decision point.

---

## Phase 4 — Orchestrator: segment the monolith + count bands

Refactor `run_skill_batch` (`qngen/skills/shared/orchestrator.py`) from one
draft→critique→revise megacall into a generic **blueprint-driven runner**:

```
run_blueprinted_generation(blueprint_slots, skill, repair_loop, polish)
```

- One focused call per slot (more reliable than one giant call).
- `critique/revise` → optional **Polish** step, per slot, only where it adds value
  (flashcard definition merge, scenario rubric tightening).
- Counts come from the blueprint; the model never decides quantity unbounded.

---

## Count model (applies across artifacts)

| Artifact   | Floor (importance)     | Per-chapter band   | Who decides within band   |
|------------|------------------------|--------------------|---------------------------|
| Flashcards | essential + supporting | 3–8                | model curation            |
| Questions  | objective-linked       | 3 + 1/subsection   | structure (deterministic) |
| Scenarios  | essential only         | 1–3                | model curation            |

Bands exposed as config (`qngen.*`) so they're tunable. Output varies run-to-run
with content richness, but always within a predictable scale.

---

## Agentic strategy

- **Adopt:** the bounded generate→check→revise *pattern* (Phases 1 & 4), on the
  existing `LLMClient`. No new dependency.
- **Defer:** the full Claude Agent SDK (autonomous tools/filesystem/permissions).
  QnGen inputs are already grounded and structured; escalate to retrieval-tool
  agents **only if** grounding errors persist after Phase 1 — an evidence-driven
  later decision, documented as a fallback, not a commitment.

---

## Sequencing, files, risk

- **Phase 1 first** — independent, fixes the visible inconsistency, fully
  verifiable.
- **0 → 2 → 3 → 4** — structural redesign, depends on Phase 0.
- Stage versions bump (`2.1`/`3.0`) so old runs stay reproducible.

| Phase | Files |
|-------|-------|
| 0     | `worker/stage_executor.py`, `qngen/canonical_context.py` |
| 1     | `qngen/validators.py`, `qngen/skills/flashcards/helpers.py`, `qngen/skills/shared/orchestrator.py` |
| 2     | `qngen/skills/questions/SKILL.md`, `qngen/stages/quiz_gen.py` |
| 3     | `qngen/skills/scenarios/SKILL.md`, `qngen/stages/scenario_gen.py` |
| 4     | `qngen/skills/shared/orchestrator.py`, all three stages, `config.py` (bands) |
| tests | validator-repair-loop tests, dedup tests, blueprint tests |
