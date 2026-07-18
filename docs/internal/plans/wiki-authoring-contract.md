# Wiki Authoring Contract

The data contract for manual knowledge curation: the author reads the ebook,
writes unstructured notes (terminology, concepts, terms, insights), and uploads
them. A single structuring LLM call converts the notes into proposed wiki
entries; the server enriches them with slugs, duplicate resolution, and
evidence links; the author reviews and edits; a commit promotes them into
`wiki_entries` as `canonical`.

This document defines every payload in that lifecycle. The implementation plan
lives in [wiki-authoring-plan.md](wiki-authoring-plan.md).

## Lifecycle

```
author notes (unstructured)
        │  POST /wiki/ingest-batches
        ▼
┌─────────────────────────────┐
│ 1. Structuring LLM call     │  notes → structured entries (strict JSON schema)
│ 2. Server enrichment        │  slug · duplicate resolution · evidence linking
└─────────────────────────────┘
        │  batch saved as status: draft
        ▼
   Review UI (edit / merge / drop / re-link)
        │  PATCH /wiki/ingest-batches/{id}      (save edits)
        │  POST  /wiki/ingest-batches/{id}/commit
        ▼
   wiki_entries rows (status: canonical) + embeddings
        ▼
   QnGen flashcards / questions / scenarios
```

A batch is the unit of upload — typically one chapter's worth of reading
notes. Batches persist in `wiki_ingest_batches` so the author can structure
notes today and review/commit days later.

---

## 1. Knowledge dump (author → API)

`POST /workspaces/{workspace_id}/wiki/ingest-batches`

```json
{
  "notes": "Enemy system — Warden's idea that the enemy isn't a line of troops but a system of interdependent parts (leadership, processes, infrastructure, population, fielded forces). Attack the system, not the soldier.\n\nCenter of gravity: the hub of power everything depends on. Clausewitz. Related to enemy system — the enemy system model is basically a way to FIND the COG.\n\ninsight: strategic paralysis beats attrition — you win faster and cheaper by shutting the system down than by grinding its army away.\n\nOODA loop (Boyd) — observe, orient, decide, act. Tempo weapon: cycle faster than the enemy and his decisions arrive too late to matter.",
  "source_id": "6f1b2c3d-…",
  "chapter_hint": "3",
  "title": "Ch. 3 reading notes"
}
```

| Field | Required | Meaning |
|-------|----------|---------|
| `notes` | yes | Raw unstructured text. Free-form: fragments, bullets, prose, `term: definition` pairs, "insight:" prefixes — anything. Capped at `wiki_authoring.max_notes_chars` (default 24 000). |
| `source_id` | no (strongly recommended) | The ebook the notes came from. Enables evidence linking and chapter resolution. Entries committed without a source get no evidence and are invisible to QnGen (wiki/assistant only). |
| `chapter_hint` | no | Chapter number **or** title fragment. Resolved against `document_chapters` (by `sequence_index`, then case-insensitive title match). Restricts evidence search to that chapter's segments and pre-fills chapter assignment in review. |
| `title` | no | Display label for the batch list. Defaults to `"Notes — {created_at}"`. |

Deliberate non-goals for the input: no required structure, no markup
conventions the author must remember. Conventions the model *does* understand
when present (all optional): `term: definition` lines, an `insight:` prefix,
`aka …` for aliases, `(essential)` / `(minor)` importance cues.

---

## 2. Structuring output (LLM → server)

One `complete_json` call with a **strict structured-output schema** (per
`docs/external/openai/structured-output.md`). The model sees only the notes
plus the resolved chapter/source titles — never the ebook text — so it cannot
invent content beyond what the author wrote.

```json
{
  "entries": [
    {
      "label": "Enemy System",
      "entry_kind": "concept",
      "definition": "Warden's model of the enemy as a system of interdependent parts — leadership, organic processes, infrastructure, population, and fielded forces — rather than a line of troops. The object is to attack the system, not the soldier.",
      "aliases": ["five-ring model"],
      "pronunciation": null,
      "importance": "essential",
      "prerequisite_labels": [],
      "note_excerpt": "Enemy system — Warden's idea that the enemy isn't a line of troops but a system of interdependent parts…"
    },
    {
      "label": "Strategic Paralysis",
      "entry_kind": "insight",
      "definition": "Strategic paralysis beats attrition: you win faster and cheaper by shutting the enemy system down than by grinding its army away.",
      "aliases": [],
      "pronunciation": null,
      "importance": "supporting",
      "prerequisite_labels": ["Enemy System"],
      "note_excerpt": "insight: strategic paralysis beats attrition…"
    }
  ],
  "unparsed_fragments": []
}
```

### Field rules

| Field | Type | Rules |
|-------|------|-------|
| `label` | string | Title-case noun phrase, ≤ 80 chars. Becomes `preferred_label`. |
| `entry_kind` | `"term" \| "concept" \| "insight"` | Matches the `wiki_entries_entry_kind_check` constraint. `term` = vocabulary with a compact definition; `concept` = an idea/model/framework; `insight` = an author takeaway or judgment (preserve the author's voice). |
| `definition` | string | 1–4 sentences. **Grounded in the notes only** — the model may fix grammar and expand shorthand, never add facts the author didn't write. |
| `aliases` | string[] | Alternate names present in the notes (`aka`, parentheticals, abbreviations). |
| `pronunciation` | string \| null | Only when the notes give one. |
| `importance` | `"essential" \| "supporting" \| "contextual"` | Default `supporting`. Only `essential`/`contextual` when the author signals it ("key idea", "(minor)", emphasis). Importance inflation was a core failure of machine extraction — the model must not re-introduce it. |
| `prerequisite_labels` | string[] | Only when the notes explicitly relate entries ("related to X", "builds on Y"). Resolved to `prerequisites` UUIDs at commit via `resolve_prerequisites` semantics (labels that match nothing are dropped silently). |
| `note_excerpt` | string | Verbatim fragment (≤ 240 chars) of the notes this entry came from. Shown in review so the author can audit fidelity. Stored in `origin`. |
| `unparsed_fragments` | string[] | Leftover note text the model could not confidently structure. Surfaced in review — nothing is ever silently dropped. |

### Structuring prompt requirements (behavioral spec)

1. **Split, don't summarize.** Each atomic term/concept/insight in the notes
   becomes its own entry; compound lines are split.
2. **Merge within the batch.** Obvious restatements of the same item collapse
   into one entry (aliases merged).
3. **No invention.** Definitions may only rephrase the author's words. If a
   note names a term without defining it, emit the entry with the best
   available fragment as the definition — review will catch it.
4. **Insights keep the author's voice.** Light grammar cleanup only.
5. **Deterministic classification.** Vocabulary → `term`; models/frameworks/
   ideas → `concept`; judgments/takeaways/lessons → `insight`.
6. Anything ambiguous goes to `unparsed_fragments`, never guessed into an
   entry.

---

## 3. Enriched proposal (server → review UI)

After the LLM call, the server enriches each entry **without any further LLM
involvement** and persists the batch. `GET /wiki/ingest-batches/{id}` returns:

```json
{
  "id": "9a8b7c…",
  "workspace_id": "…",
  "source_id": "6f1b2c3d-…",
  "title": "Ch. 3 reading notes",
  "status": "draft",
  "raw_notes": "…verbatim input…",
  "chapter": {
    "chapter_id": "d4e5f6…",
    "title": "The Enemy as a System",
    "sequence_index": 3
  },
  "unparsed_fragments": [],
  "entries": [
    {
      "index": 0,
      "label": "Enemy System",
      "entry_kind": "concept",
      "definition": "…",
      "aliases": ["five-ring model"],
      "pronunciation": null,
      "importance": "essential",
      "prerequisite_labels": [],
      "note_excerpt": "…",

      "canonical_slug": "enemy-system",
      "resolution": "new",
      "existing_entry_id": null,
      "existing_definition": null,
      "similar_entries": [],

      "evidence_status": "linked",
      "evidence": [
        {
          "segment_id": "a1b2…",
          "sequence_index": 412,
          "page": 87,
          "similarity": 0.63,
          "preview": "The enemy is a system composed of numerous subsystems…",
          "reader_link": "/app/reader/6f1b2c3d-…?seg=412"
        }
      ],

      "include": true
    }
  ],
  "model": "gpt-…",
  "cost_usd": 0.004,
  "created_at": "…",
  "updated_at": "…"
}
```

### Enrichment fields

| Field | Values | Semantics |
|-------|--------|-----------|
| `canonical_slug` | string | `normalize_slug(label)`, with the merge-group suffix rule from `wiki_promotion._wiki_slug_for_concept` (a term and a concept for the same subject share a slug; an insight diverges to `slug--insight`). |
| `resolution` | `new` | No existing entry with this slug. Commit inserts. |
| | `merge` | Existing entry, definitions compatible (per `_definitions_conflict`). Commit merges aliases/evidence into the existing row, exactly like pipeline promotion. |
| | `conflict` | Existing entry, definitions disagree. Review UI shows both; the author picks (their choice wins — no `wiki_disputes` row for the manual path, the human *is* the dispute resolution). |
| `existing_entry_id` / `existing_definition` | | Populated for `merge`/`conflict`. |
| `similar_entries` | `[{id, label, similarity}]` | Advisory embedding-similarity matches (≥ `wiki_authoring.dedup_similarity_threshold`, default 0.85) against existing wiki entries whose slug differs — catches "OODA Loop" vs "Boyd Cycle". Never blocks; shown as a badge. |
| `evidence_status` | `linked` | ≥ 1 segment matched at or above `wiki_authoring.evidence_threshold` (default 0.45). |
| | `weak` | Matches exist only between the weak floor (0.30) and the threshold — attached but flagged for a look. |
| | `unlinked` | Nothing matched, or the batch has no `source_id`. Entry still commits; it just won't feed QnGen until linked. |
| `evidence` | array | Top `wiki_authoring.evidence_top_k` (default 3) rows from `match_ndr_segments`, embedding `"{label} — {definition}"`, filtered to `source_id` and (when a chapter is resolved) to that chapter's `segment_ids` from `document_chapters`. `reader_link` uses the stable `sequence_index` deep-link. |
| `include` | bool | Review checkbox; `false` entries are skipped at commit. |

Notes-are-paraphrases means exact-quote verification (the old extraction
Phase 1 check) does not apply here: evidence records carry `segment_id` +
`page` but no `quote` field.

### Review edits

`PATCH /wiki/ingest-batches/{id}` accepts the full `entries` array back
(edited labels, definitions, kinds, importance, `include` flags, and manually
adjusted `evidence` — the UI offers a chapter/section picker built from
`document_chapters.sections` for unlinked entries). Editing a `label` clears
`canonical_slug`/`resolution`; the server recomputes both before saving.
Batches are only editable while `status = "draft"`.

---

## 4. Commit (review UI → wiki)

`POST /workspaces/{workspace_id}/wiki/ingest-batches/{id}/commit`

No body — the batch's saved draft state is the commit payload (one source of
truth; no drift between what was reviewed and what lands). The server:

1. Re-validates every included entry against **current** `wiki_entries`
   (another batch may have committed since review). Any entry whose
   `resolution` silently changed comes back as `409` with the refreshed
   entries so the author re-confirms — commits never overwrite unseen state.
2. Runs the promotion path (shared semantics with `promote_concepts_to_wiki`):
   - `new` → insert with the row mapping below.
   - `merge` → union aliases, merge evidence records (dedup on
     `(source_id, segment_id)`), keep the higher importance, keep the existing
     definition.
   - `conflict` → apply whichever definition the author chose in review.
3. Resolves `prerequisite_labels` → `prerequisites` UUIDs across the full
   post-commit workspace wiki.
4. Embeds every inserted/updated entry (`"{preferred_label} — {definition}"`,
   `text-embedding-3-small`) into `wiki_entries.embedding` so the Reader
   assistant's precision channel sees them immediately.
5. Marks the batch `status: "committed"` and stamps `committed_at` +
   `committed_entry_ids`.

`POST …/discard` marks the batch `discarded`. Both transitions are terminal.

### Row mapping (entry → `wiki_entries`)

| Contract field | Column | Notes |
|----------------|--------|-------|
| `label` | `preferred_label` | |
| `canonical_slug` | `canonical_slug` | unique per workspace (existing constraint) |
| `definition` | `definition` | |
| `pronunciation` | `pronunciation` | |
| `aliases` | `aliases` | |
| `entry_kind` | `entry_kind` | |
| `importance` | `importance` | |
| — | `status` | always `"canonical"` — drafts live in the batch table, so the status constraint needs no new value |
| `evidence[]` | `evidence` | `[{source_id, segment_id, page}]`; `[]` when unlinked |
| resolved prerequisites | `prerequisites` | UUID array |
| — | `origin` | `{"kind": "manual", "batch_id": …, "note_excerpt": …, "chapter_id": …, "chapter_sequence_index": …}` |
| — | `confidence`, `selection_score` | `null` — extraction-era signals, meaningless for human-curated entries |

`origin.kind = "manual"` is the marker that distinguishes curated entries from
legacy machine-extracted ones for migration/cleanup queries.

---

## 5. Storage: `wiki_ingest_batches`

```sql
create table public.wiki_ingest_batches (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  title text not null,
  raw_notes text not null,
  chapter_hint text,
  chapter jsonb,                        -- resolved {chapter_id, title, sequence_index}
  status text not null default 'draft',
  entries jsonb not null default '[]',  -- enriched proposal entries (contract §3)
  unparsed_fragments jsonb not null default '[]',
  model text,
  cost_usd numeric,
  committed_entry_ids uuid[] not null default '{}',
  committed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint wiki_ingest_batches_status_check
    check (status in ('draft', 'committed', 'discarded'))
);
```

Draft entries deliberately live as jsonb here rather than as provisional
`wiki_entries` rows: the wiki table stays 100 % canonical (QnGen, the
assistant, and the slug-uniqueness constraint never see half-reviewed data),
and a discarded batch leaves zero residue.

---

## Endpoint summary

| Method & path | Purpose |
|---------------|---------|
| `POST /workspaces/{ws}/wiki/ingest-batches` | Upload dump → structure → enrich → save draft |
| `GET /workspaces/{ws}/wiki/ingest-batches?status=` | List batches |
| `GET /workspaces/{ws}/wiki/ingest-batches/{id}` | Fetch batch for review |
| `PATCH /workspaces/{ws}/wiki/ingest-batches/{id}` | Save review edits (drafts only) |
| `POST /workspaces/{ws}/wiki/ingest-batches/{id}/commit` | Promote to canonical wiki entries |
| `POST /workspaces/{ws}/wiki/ingest-batches/{id}/discard` | Terminal discard |
| `POST /workspaces/{ws}/wiki/entries` | Single manual entry, no LLM (quick add) |
| `PATCH /workspaces/{ws}/wiki/entries/{id}` | Edit a canonical entry (re-embeds on definition change) |
| `DELETE /workspaces/{ws}/wiki/entries/{id}` | Sets `status: "deprecated"` (soft delete; QnGen/assistant filter it out) |

## Config (`wiki_authoring.*`)

| Setting | Default | Meaning |
|---------|---------|---------|
| `max_notes_chars` | 24 000 | Dump size cap (one chapter's notes; keeps structuring a single sync call) |
| `evidence_top_k` | 3 | Segments attached per entry |
| `evidence_threshold` | 0.45 | `linked` floor (stricter than the assistant's 0.30 recall threshold — linking is a precision problem) |
| `evidence_weak_floor` | 0.30 | Below threshold but above this → `weak` |
| `dedup_similarity_threshold` | 0.85 | Advisory `similar_entries` floor |

The structuring model is resolved through the existing per-action LLM routing
(`llm.resolve_action("wiki-structuring")`), consistent with every other stage.
