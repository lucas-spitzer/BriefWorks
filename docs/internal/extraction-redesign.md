# Knowledge Extraction Redesign Plan

How `extract-chapter-knowledge` decides which terms, concepts, and insights
become canonical wiki entries — and how to make that decision deliberate,
calibrated, and bounded. The wiki layer is the sole input to QnGen, so its
selectivity drives every downstream count and quality issue.

## Background: how selection works today

1. Per-chapter **objectives** are generated, then per-chapter **extraction**
   (`extract_chapter_knowledge.py`, `CONCEPTS_SYSTEM_PROMPT`) asks the model to
   "identify what a reader must understand," emitting items with `entry_kind`
   (term/concept/insight), self-declared `importance`, `confidence`,
   `evidence_segment_ids`, `evidence_quotes`, `objective_labels`.
2. A coarse **salience gate** keeps an item only if
   `importance ∈ {essential, supporting}` OR `salience ≥ 0.35` (salience is a
   positional + size heuristic).
3. **Slug-merge** dedups by `(normalized_slug, entry_kind)`, then a single
   **LLM consolidation** pass merges near-duplicates and re-assigns importance.
4. **Promotion** (`wiki_promotion.py`) inserts every new slug as
   `status: "canonical"` immediately. Conflicting definitions → `disputed`.

## The core problem

Extraction is **maximal-pull** and promotion is **accept-all**:

- **No promotion threshold.** Every item with a label + definition becomes
  canonical. `confidence` is captured and merged but never gates anything. Entry
  count = "whatever the model emits per chapter" → the 100+ flood.
- **Importance is self-declared per item, no rubric or budget** → inflation
  ("everything essential"), which defeats QnGen's importance-based filtering.
- **Dedup is slug-local** → case/wording variants (`Enemy system` vs
  `enemy system`) survive as separate canonical entries.

## Design principles

1. **Promote the deserving few, don't accept everything extracted.** Selection
   is an explicit, scored decision with a budget — not a side effect of how much
   the model emitted.
2. **Importance is relative, not self-declared.** Rank within a chapter/document
   and bucket; never let each item rate itself in isolation.
3. **Use signals already captured.** Evidence strength, confidence, objective
   linkage, and recurrence exist in-flight today but gate nothing — wire them in.
4. **Gate at the canonical boundary.** QnGen reads only `canonical`; making
   promotion deliberate gives the whole downstream pipeline one tunable quality
   gate.
5. **Bounded, config-driven counts.** Per-chapter/per-document caps so the wiki
   scales with content richness, not corpus length.

---

## Phase 0 — Foundations (schema + config, additive)

- **Migration:** extend `wiki_entries_status_check` to allow a new
  `candidate` status; add a nullable `selection_score float` (and optionally
  `confidence float`) column so the promotion decision is auditable. Index stays
  on `(workspace_id, status)`; QnGen keeps filtering `status = 'canonical'`, so
  candidates are auto-excluded with zero QnGen changes.
- **Config:** add `intellex.*` knobs — per-chapter/per-document entry caps,
  per-importance-tier caps, and `selection_score` / `confidence` thresholds.
- Backward-compatible: defaults reproduce today's behavior until later phases
  turn gating on.

Files: `supabase/migrations/`, `app/config.py`, `concept_models.py`.

---

## Phase 1 — Standalone quality wins (ship first, low-risk)

1. **Evidence-quote verification** — verify each `evidence_quote` actually
   appears in its cited segment text; drop/penalize hallucinated grounding
   before it can become an entry. (`extract_chapter_knowledge.py` post-parse.)
2. **Case/normalization dedup at promotion** — collapse case-variant labels on a
   normalized key (casefold) in `merge_knowledge_items` / `wiki_promotion.py`,
   the same fix applied downstream in QnGen flashcards but at the source.

Verifiable outcome: hallucinated-evidence entries and case-duplicate entries
disappear; no behavioral dependency on later phases.

---

## Phase 2 — Comparative importance calibration

Stop trusting per-item self-rated importance.

- After extraction/consolidation, **rank candidates within each chapter and
  document** by a composite signal and **bucket by quantile** into
  essential/supporting/contextual — OR give the model an explicit distribution
  rubric ("essential = the ≤3–5 load-bearing ideas a reader cannot pass the
  chapter without").
- Relative ranking removes inflation, restoring a meaningful `importance` signal
  for QnGen (fixes the scenario flood and the essential-only filter that doesn't
  filter).

Files: `extract_chapter_knowledge.py` (consolidation prompt + a post-pass
ranker), new `app/intellex/selection.py`.

---

## Phase 3 — Scored selection + candidate→canonical gating (core)

The direct answer to "decide which are chosen." **The gate is an LLM curation
pass** (decided), not a pure threshold.

- **Signal pre-pass** (`selection.py`): compute a `selection_score` from evidence
  strength (verified quote count + segment count), `confidence`, objective
  linkage, and cross-chapter recurrence. These scores are inputs the curator
  sees, not the final decision.
- **LLM "wiki editor" curation** (the extraction analog of QnGen's blueprint
  curation): given the candidate set for a chapter/document plus their signals
  and a per-chapter/per-document **budget** (Phase 0 config bands), the model
  selects the durable entries and demotes the rest. Promote the selected set as
  `canonical`; insert the remainder as `status: "candidate"`.
- Since QnGen consumes only `canonical`, this single gate filters the entire
  downstream pipeline; tuning the budget tunes total output.
- Apply the same bounded generate→check pattern used in QnGen (validate the
  curator's selection against the budget and grounding; never exceed the cap).

Files: `wiki_promotion.py`, `selection.py`, `extract_chapter_knowledge.py`,
`worker/stage_executor.py` (persist `selection_score`, bump stage version).

---

## Phase 4 — Embedding-based semantic dedup

- Replace reliance on the single LLM consolidation batch with **embedding
  similarity clustering across the whole document**; merge within clusters
  before promotion.
- Catches near-duplicates that differ in wording/slug and span consolidation
  batches.

**Note:** the assumed pre-existing embeddings client did not exist — a new
`app/services/embeddings.py` (OpenAI `text-embedding-3-small`) was added. The
dedup is **off by default** (`EXTRACT_EMBEDDING_DEDUP=false`) since it adds
per-extraction embedding API cost; enable per workspace/source.

Files: `app/services/embeddings.py` (new), `extract_chapter_knowledge.py`,
`config.py`.

---

## Phase 5 — Objective coverage + entry_kind policy

**Implemented — objective coverage (`selection.py`, `extract_chapter_knowledge.py`):**
- `objective_concept_slugs()` captures the objective↔concept linkage *before*
  consolidation (where `objective_labels` is reliable; consolidation can drop it).
- `ensure_objective_coverage()` then, after calibration: backfills each
  objective's `concept_labels` from its linked concepts (they start empty, and
  QnGen's blueprint matches on them — this closes the loop end-to-end through the
  persisted `extract.chapters` block), and guarantees every objective is backed
  by ≥1 essential concept (promoting the highest-scoring linked concept,
  overriding the quantile where needed).

**Deferred (with rationale):**
- **entry_kind→artifact quotas** (terms→flashcards, concepts→questions,
  insights→scenarios): the high-value version is a *QnGen-side* filter (which
  pool feeds which artifact), not an extraction change — it belongs with a QnGen
  follow-up, not here. Forcing per-kind quotas in extraction risks dropping good
  standalone entries that the curation gate already handles.
- **Salience upgrade:** positional salience now only gates which low-salience
  chapters contribute contextual items at extraction time; with comparative
  calibration + the curation gate downstream, reworking it is low-value. Left
  as-is.
- **Aggressive pruning of objective-less concepts:** the Phase 3 curation gate
  already prunes (candidate vs canonical); a second pruning here would conflict.

---

## Sequencing, files, risk

- **Phase 1 first** — independent, immediately reduces hallucinated/duplicate
  entries, fully verifiable.
- **0 → 2 → 3** is the spine: foundations, then calibrated importance, then the
  scored gate. **4 → 5** are refinements.
- Bump `extract-chapter-knowledge` stage version so prior runs stay
  reproducible. Re-running extraction is required for sources to gain the new
  selectivity (and to populate `extract.chapters` for QnGen's blueprint path).

| Phase | Files |
|-------|-------|
| 0 | `supabase/migrations/`, `app/config.py`, `concept_models.py` |
| 1 | `extract_chapter_knowledge.py`, `wiki_promotion.py` |
| 2 | `extract_chapter_knowledge.py`, `app/intellex/selection.py` (new) |
| 3 | `wiki_promotion.py`, `selection.py`, `extract_chapter_knowledge.py`, `worker/stage_executor.py` |
| 4 | `selection.py` / `extract_chapter_knowledge.py`, embeddings client |
| 5 | `extract_chapter_knowledge.py`, `selection.py` |
| tests | quote-verification, casefold-dedup, importance-ranking, scorer + gating, dedup-cluster tests |

## Relationship to the QnGen redesign

This is upstream of [qngen-redesign.md](qngen-redesign.md). The QnGen blueprint
already consumes `importance` and `canonical` status; Phases 2–3 here make those
signals trustworthy, so the two redesigns compound: calibrated, bounded wiki
entries → predictable, well-grounded assessments.
