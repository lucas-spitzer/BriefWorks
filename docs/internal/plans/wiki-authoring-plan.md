# Wiki Authoring Implementation Plan

> **Implemented.** One naming deviation from the plan below: the
> producer-neutral promotion module shipped as `intellex/wiki_candidates.py`
> (not `wiki_promotion.py` — that name stayed with the deleted extraction-era
> file until it was removed). Everything else matches this plan; treat the
> code as authoritative over file names mentioned here.

Replace automated knowledge extraction with human-curated wiki authoring. The
author reads the generated ebook, writes unstructured notes, and uploads them;
a structuring LLM call converts notes into the wiki-entry JSON contract; a
review/commit step promotes them to canonical `wiki_entries`; QnGen then
generates flashcards, questions, and scenarios from the curated wiki.

The data contract (payloads, schemas, endpoint shapes, config) is specified in
[wiki-authoring-contract.md](wiki-authoring-contract.md). This document covers
sequencing, file-level changes, and the pipeline/QnGen fallout.

## Background: why

Machine extraction was maximal-pull with accept-all promotion —
[extraction-redesign.md](extraction-redesign.md) documents the 100+ entry
floods, importance inflation, and duplicate variants, and proposed a five-phase
algorithmic gate to fix it. This plan supersedes that approach: the analysis
and evaluation that extraction tried to automate is done by the author while
reading, and the machine's job shrinks to *formatting* (notes → JSON) and
*grounding* (linking entries back to source segments). For a single-user
production studio, a human curator is a strictly better selection gate than a
tuned scoring pipeline.

What survives unchanged:

- **The entire ebook artifacts pipeline.** `create-ebook` and the narration
  stages consume `document_chapters` from the structuring/chunk stages;
  nothing in Mathesys depends on extraction output.
- **The wiki as QnGen's sole input.** The gate-at-the-canonical-boundary
  principle from the extraction redesign holds; only the producer changes.
- **The QnGen redesign** ([qngen-redesign.md](qngen-redesign.md)) — its repair
  loops, validators, and count bands all still apply (Phase 4 below adjusts
  its chapter-blueprint inputs).

## Target workflow

1. Upload source → production run with ebook artifact(s) → base ingest +
   `create-ebook` (extraction no longer runs).
2. Read the ebook in ElevenReader/Speechify, writing notes per chapter.
3. Paste a chapter's notes into the Wiki authoring UI → structuring call →
   enriched draft batch.
4. Review: edit definitions, fix classifications, resolve conflicts, confirm
   evidence links, drop noise.
5. Commit → canonical wiki entries (embedded for the assistant).
6. Repeat 3–5 per chapter until the book is curated.
7. Launch an **assessment-only production run** (flashcards/quizzes/scenarios)
   against the already-ingested source.

## Design principles

1. **The human curates; the machine formats and grounds.** The structuring
   call never adds knowledge, never rates importance on its own, and never
   writes to `wiki_entries` directly — every entry passes through review.
2. **Reuse the promotion machinery.** Slug normalization, merge-group
   suffixing, alias/evidence merging, and conflict detection in
   `wiki_promotion.py` are producer-agnostic. The manual path adapts to them
   rather than reimplementing.
3. **Preserve grounding.** QnGen's quality rests on evidence segments
   (`build_source_concepts` drops evidence-less entries; prompts feed evidence
   text to the model). Manual entries regain grounding through embedding-based
   evidence linking against `ndr_segments` — infrastructure that already
   exists (migration 31, `services/embeddings.py`, `match_ndr_segments`).
4. **Old pipeline keeps working until the new path is proven.** Extraction is
   removed from `BASE_PIPELINE` only in Phase 3, after the authoring flow is
   verified end-to-end; code deletion waits for Phase 5.
5. **Drafts never touch `wiki_entries`.** The canonical table stays canonical;
   review state lives in `wiki_ingest_batches`.

---

## Phase 0 — Contract, schema, config (additive, zero behavior change)

- **Migration `33-add-wiki-ingest-batches.sql`** — the `wiki_ingest_batches`
  table per contract §5, plus RLS/grants consistent with the existing tables
  (API talks through the service role; workspace_id is the tenancy boundary).
- **Config** — new `WikiAuthoringSettings` dataclass in `api/app/config.py`
  (`max_notes_chars`, `evidence_top_k`, `evidence_threshold`,
  `evidence_weak_floor`, `dedup_similarity_threshold`) wired into `Settings`;
  register a `wiki-structuring` action in the per-action LLM routing so the
  model is swappable like every other stage.
- **Models** — `api/app/models/wiki_ingest.py`: `WikiIngestCreate`,
  `WikiIngestEntry` (the enriched-entry shape, contract §3),
  `WikiIngestBatchResponse`, `WikiIngestBatchUpdate`. Extend
  `models/wiki_entry.py` with `WikiEntryCreate` / `WikiEntryUpdate` for CRUD.

Files: `supabase/migrations/33-add-wiki-ingest-batches.sql`,
`api/app/config.py`, `api/app/models/wiki_ingest.py`,
`api/app/models/wiki_entry.py`.

---

## Phase 1 — Backend authoring flow (the core build)

### 1a. Structuring service — `api/app/services/wiki_authoring.py`

- `structure_notes(notes, *, chapter, source) -> StructuredNotes` — one
  `OpenAIClient.complete_json` call against the strict schema (contract §2),
  with the behavioral prompt spec from the contract (split-don't-summarize,
  no invention, author-voice insights, `unparsed_fragments` for leftovers).
  Runs synchronously in the request (same pattern as the assistant router —
  a notes batch is one call, seconds not minutes; the RQ queue stays out of
  it unless latency proves otherwise).
- `resolve_chapter(chapter_hint, source_id)` — match against
  `document_chapters` by `sequence_index`, else case-insensitive title
  fragment; returns the resolved chapter block or `null`.

### 1b. Enrichment — same service

- **Slugs + duplicate resolution:** `normalize_slug` + the merge-group suffix
  rule; compare against current workspace entries to set
  `resolution: new | merge | conflict` using `_definitions_conflict` from
  `wiki_promotion.py` (refactor those two helpers to a shared location so the
  API doesn't import stage internals).
- **Evidence linking:** embed `"{label} — {definition}"` per entry (one
  batched `EmbeddingClient.embed` call, via `asyncio.to_thread` like
  `RetrievalService`), then `RetrievalRepository.match_segments` filtered to
  `source_id`; when a chapter resolved, intersect with the chapter's
  `segment_ids` (including `sections` from migration 32). Classify
  `linked / weak / unlinked` per the contract thresholds. No quote field —
  notes are paraphrases, exact-quote verification doesn't apply.
- **Advisory dedup:** cosine similarity of the entry vector against existing
  `wiki_entries.embedding` (reuse `match_wiki_entries`) → `similar_entries`.
- Persist the batch (`status: draft`) with model + cost metadata.

### 1c. Commit — same service + promotion refactor

- Introduce a producer-neutral `WikiCandidate` model (label, slug, kind,
  definition, aliases, pronunciation, importance, prerequisite_labels,
  evidence records, origin) and refactor `promote_concepts_to_wiki` /
  `resolve_prerequisites` to operate on it; the extraction stage keeps working
  through a thin `DeconstructedConcept → WikiCandidate` adapter until Phase 5
  deletes it.
- Commit flow per contract §4: re-validate resolutions against current state
  (409 on drift), insert/merge through the shared promotion logic, resolve
  prerequisites, **embed all touched entries** into `wiki_entries.embedding`,
  stamp the batch `committed`.
- Manual-path conflict handling: the author's reviewed choice wins outright —
  no `wiki_disputes` row (the human is the dispute resolution).

### 1d. Routers + repositories

- `api/app/routers/wiki.py` — add the ingest-batch endpoints and wiki CRUD
  per the contract's endpoint summary. `DELETE` on an entry sets
  `status: "deprecated"` (soft delete — QnGen and the assistant already
  filter on `canonical`); `PATCH` re-embeds when the definition changes.
- `api/app/repositories/wiki_entries.py` — add `insert`, `update`,
  `update_embedding`; new `api/app/repositories/wiki_ingest_batches.py`.
- `api/app/dependencies/services.py` — providers for the new repository and
  service.

**Tests** (`api/tests/test_wiki_authoring.py`): structuring-schema parse +
prompt-contract fixtures; slug/resolution matrix (new/merge/conflict, term-vs-
insight suffixing); evidence classification across the three thresholds (mock
embeddings); commit idempotence + drift-409; prerequisite resolution;
deprecated entries invisible to QnGen context.

**Verifiable outcome:** full curl-level loop — dump → draft → edit → commit →
entries queryable via the existing wiki list endpoint with evidence attached —
before any UI or pipeline change.

---

## Phase 2 — Frontend: Wiki console

New Foundry section (pattern-match `FoundryAssessments` / `FoundryStages`):

- **Entry browser** — list with kind/importance/status chips, search (existing
  endpoint already supports it), inline editor, deprecate action, evidence
  chips deep-linking into the Reader (`reader_link` from the contract).
- **Ingest flow** — "Add knowledge" → paste notes + pick source/chapter →
  structuring spinner → **review table**: editable rows; kind + importance
  selects; resolution badges (`new` / `merge` / `conflict` with side-by-side
  definitions on conflict); `similar_entries` badge; evidence status with a
  chapter/section picker (from `document_chapters.sections`) for
  unlinked/weak rows; include-checkboxes; `unparsed_fragments` rendered under
  the table so dropped text is visible. Save (PATCH) and Commit actions.
- **Batch list** — drafts resumable across sessions, committed/discarded
  history.

Files: `app/src/components/foundry/FoundryWiki.tsx` (+ subcomponents),
`app/src/lib/wikiApi.ts`, wiring in `FoundryShell.tsx`/`FoundryPage.tsx`,
`app/src/foundry.css`.

---

## Phase 3 — Decouple the pipeline (the cutover)

Now that curation works end-to-end, remove extraction from the run path and
make assessments runnable after curation:

1. **`api/app/pipeline.py`** — drop the `extract-knowledge` step from
   `BASE_PIPELINE`.
2. **`api/app/intellex/source_readiness.py`** — delete
   `source_extract_complete`; drop `has_extract_stage_run` from
   `source_intellex_complete`. Ripples: `pipeline_runner.execute` (readiness
   probe) and the QnGen gate in `stage_executor.py`.
3. **QnGen gate** (`stage_executor.py` ~950–982) — replace the
   extract-stage-run requirement with the new readiness; replace the two
   error messages: "not intellex-complete → run ingest" and "no canonical
   wiki concepts with evidence for this source → curate wiki entries (with
   evidence links) before generating assessments".
4. **Assessment-only runs** — mostly free already: `execute()` marks
   intellex-complete sources and every ingest step reuses them, so a run with
   `target_artifacts: ["flashcards"]` against a curated source skips straight
   to QnGen. Verify the store/parse steps tolerate reuse without re-download;
   add a "Generate assessments" launcher in the console that creates such a
   run (sources filtered to intellex-complete + has canonical wiki entries).
5. **`pipeline_runner.py`** — delete `run_extract_chapter_knowledge_step` and
   its call site; stop probing `has_extract_stage_run`.
6. Keep `source-research` — its metadata slice feeds narration and is
   independent of extraction.

Historical runs keep their recorded pipelines (stage rows are data, not code
references, and completed runs are never re-executed) — no backfill needed.

**Tests:** readiness without extract; QnGen gate messages; assessment-only run
against a pre-ingested fixture source.

---

## Phase 4 — QnGen adjustments for curated input

- **Immediate behavior (no code change needed):** with `extract.chapters`
  absent for new sources, `build_chapter_blueprint` returns `[]` and all three
  skills fall back to flat concept batching. That's acceptable now in a way it
  wasn't before: the fan-out problem was 100+ junk concepts; a curated wiki is
  small and importance-honest, so counts track curation directly.
- **Restore chapter grouping from real structure:** build the chapters block
  from `document_chapters` (+ `sections`) instead of extraction output — a
  `chapters_from_document_chapters()` helper in `qngen/canonical_context.py`
  producing `{chapter_id, chapter_title, sequence_index, segment_ids,
  objectives: []}`. Evidence-segment intersection then re-enables per-chapter
  question/scenario bands with zero extraction dependency. Entries whose
  `origin` carries a `chapter_id` group deterministically even without
  evidence.
- **`learning_objectives`:** passed as `[]` (already tolerated). The
  objective-driven question blueprint (qngen-redesign Phase 2) reads
  objectives from chapters; with none present, questions key off curated
  concepts + sections. **Deferred:** an optional `objectives` field in the
  dump contract (v1.1) — the author is forming them while reading anyway;
  revisit after living with concept-driven questions.
- **Count sanity pass:** revisit `qngen.*` bands (flashcards/scenarios
  per-chapter min/max) against realistic curated volumes (~5–15 entries per
  chapter instead of ~30+ extracted).

Files: `api/app/qngen/canonical_context.py`, `api/app/worker/stage_executor.py`
(qngen input assembly), `api/app/config.py` (band defaults), skill SKILL.md
tweaks if prompts reference objectives.

---

## Phase 5 — Cleanup + docs

- **Delete extraction:** `intellex/stages/extract_chapter_knowledge.py`,
  `intellex/selection.py`, the `ExtractChapterKnowledgeStageExecutor`, the
  `DeconstructedConcept → WikiCandidate` adapter, extraction prompts, and the
  `extract_*` selection/calibration knobs in `IntellexSettings` (keep
  `extract_embedding_model` — the shared vector-space setting — renamed to a
  neutral `embedding_model`). Delete extraction tests; keep and extend
  promotion tests against `WikiCandidate`.
- **Keep:** `wiki_slug.py`, refactored promotion module, `wiki_disputes`
  (harmless; still referenced by the read endpoint), `source-research`.
- **Legacy data:** existing machine-extracted entries are distinguishable
  (`origin.stage_id` vs `origin.kind = "manual"`). Recommendation: bulk-set
  legacy entries to `deprecated` per workspace once its book is re-curated —
  keeps them out of QnGen/assistant while preserving comparison data; hard
  delete later if never missed.
- **Docs:** rewrite the pipeline rules table + flowchart in
  [system-overview.md](../system/system-overview.md) (Intellex ends at
  `source-research`; wiki authoring becomes an explicit user step between
  Mathesys and QnGen); mark [extraction-redesign.md](extraction-redesign.md)
  superseded by this plan with a pointer; promote the contract doc to
  `docs/internal/system/` once the API ships (it's a durable interface spec,
  not a plan).

---

## Sequencing, risk, verification

| Phase | Ships alone? | Risk | Verified by |
|-------|--------------|------|-------------|
| 0 | yes (inert) | none | migration applies; settings load |
| 1 | yes | LLM structuring fidelity; evidence precision | curl-level dump→commit loop on real Ch. 1 notes; inspect evidence links in psql |
| 2 | yes | UI only | author a real chapter end-to-end in the console |
| 3 | **cutover** | QnGen gate regressions; reuse-path edge cases | assessment-only run on a curated source produces all three artifact types |
| 4 | yes | count bands off | per-chapter grouping visible in stage-run inputs; counts within bands |
| 5 | yes | deleting something still referenced | full test suite; grep for deleted symbols |

The critical validation gate is **between Phases 2 and 3**: curate at least one
full book with the new flow and generate assessments from it (via a manual
extract-free QnGen invocation or a temporary flag) before removing extraction
from `BASE_PIPELINE`.

| Phase | Files |
|-------|-------|
| 0 | `supabase/migrations/33-…`, `config.py`, `models/wiki_ingest.py`, `models/wiki_entry.py` |
| 1 | `services/wiki_authoring.py` (new), `routers/wiki.py`, `repositories/wiki_entries.py`, `repositories/wiki_ingest_batches.py` (new), promotion refactor (`intellex/stages/wiki_promotion.py` → shared), `dependencies/services.py` |
| 2 | `components/foundry/FoundryWiki.tsx` (new), `lib/wikiApi.ts` (new), `FoundryShell.tsx`, `FoundryPage.tsx`, `foundry.css` |
| 3 | `pipeline.py`, `source_readiness.py`, `pipeline_runner.py`, `stage_executor.py`, console run-launcher |
| 4 | `qngen/canonical_context.py`, `stage_executor.py`, `config.py`, skill docs |
| 5 | deletions + `docs/internal/system/system-overview.md`, plan cross-links |

## Open decisions (non-blocking, decide during build)

1. **Legacy extracted entries** — deprecate-per-workspace (recommended) vs
   hard delete. Decide when the first re-curated book is done.
2. **Sync structuring latency** — if real note batches push past ~30 s,
   move structuring onto RQ with a `structuring` batch status; the contract
   already isolates this behind the batch lifecycle.
3. **Objectives in the contract (v1.1)** — add only if concept-driven
   questions feel unfocused after a real curated book.
4. **`wiki_disputes` retirement** — the manual path doesn't write disputes;
   once extraction is deleted the table is write-orphaned. Leave until a
   later schema tidy.
