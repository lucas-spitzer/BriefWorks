# BriefWorks Supabase Setup

Use the numbered scripts (`01`–`04`) to bootstrap a **fresh** Supabase project. They contain the full current schema and stage seeds.

Operator patches (`alter-*.sql`, `restore-stages.sql`) are for **existing** databases only — do not include them in the greenfield loop.

## Prerequisites

- A Supabase project with **Google OAuth** configured in Auth (required for sign-in).
- The FastAPI backend uses the **service role** key for data access in V1. Client roles are revoked from application tables.

## Apply setup (fresh project)

Run the SQL files **in order** in the Supabase SQL editor (or pipe them through `psql`):

```text
supabase/setup/01-auth-and-extensions.sql
supabase/setup/02-schema.sql
supabase/setup/03-seed-stages.sql
supabase/setup/04-storage-and-rls.sql
```

Example with the Supabase CLI linked to your project:

```bash
for f in \
  supabase/setup/01-auth-and-extensions.sql \
  supabase/setup/02-schema.sql \
  supabase/setup/03-seed-stages.sql \
  supabase/setup/04-storage-and-rls.sql
do
  supabase db execute --file "$f"
done
```

Do **not** glob `supabase/setup/*.sql` — that would also pick up operator patches.

After running setup, replace the placeholder owner email in `approved_users` with your own Google account address.

## Existing database patches

Run these only on databases that already have a BriefWorks schema and need a targeted upgrade. Fresh installs from `01`–`04` already include the current shape.

| File | When to run |
|------|-------------|
| `alter-wiki-ingest-file-ingest.sql` | DB was created before wiki file-ingest support. Adds `attachments`, `transcription_error`, expands the status check (`transcribing`, `transcribed`, …), and sets `raw_notes` default to `''`. |
| `alter-drop-artifacts-bucket.sql` | Operator note only (SQL no-op). Supabase blocks dropping `storage.buckets` / `storage.objects` from SQL. After migrating objects into the `sources` bucket, purge the legacy `artifacts` bucket via the Storage API or Dashboard. |
| `restore-stages.sql` | Short pointer: re-run `03-seed-stages.sql` to repair a wiped or stale `stages` table. |

### Wiki file-ingest columns

```bash
supabase db execute --file supabase/setup/alter-wiki-ingest-file-ingest.sql
```

### Legacy `artifacts` storage bucket

1. Migrate objects: `cd api && python -m scripts.migrate_artifacts_into_sources`
2. Confirm downloads work.
3. Empty and delete the bucket: `python -m scripts.migrate_artifacts_into_sources --purge-legacy-bucket`  
   Or Dashboard: Storage → `artifacts` → Empty bucket → Delete bucket.

`alter-drop-artifacts-bucket.sql` is safe to open in the SQL editor but does not delete the bucket.

## What gets created

### Auth and extensions

- `approved_users` — internal authorization allowlist
- Extensions: `citext`, `pgcrypto`, `vector` (in `extensions` schema)
- Trigger helper: `set_updated_at()`
- RAG helpers: `match_ndr_segments`, `match_wiki_entries` (service role only)

### Core tables

- `workspaces`, `sources`, `production_runs`, `stage_runs`, `stages`
- `workspace_stage_settings` — per-workspace LLM provider/model overrides
- API cost tracking columns on `stage_runs` and `production_runs`

### Intellex content

- `ndr_segments` — chunked parsed text with page locators, optional `md`, and embeddings
- `document_chapters` — persisted chapter/section segmentation (`sections` jsonb)
- `wiki_entries` — canonical terms, concepts, and insights (`entry_kind`; optional `candidate` status)
- `wiki_disputes` — non-blocking conflict log
- `wiki_ingest_batches` — manual wiki authoring drafts (paste notes or file attachments with transcription statuses)

### Mathesys outputs

- `artifacts` — `electronic_book`, `narration_audio`, `wiki_json` (table rows; files live under `sources`)
- `narration_segments` — per-paragraph audio paths and word timings
- Storage bucket: `sources` — per-source tree under
  `workspaces/{workspace_id}/sources/{source_id}/` with the original upload
  plus sibling folders `parse/`, `structure/`, `narration/`, and
  `artifacts/{artifact_id}/`
  (no standalone `artifacts` bucket on fresh installs)

### QnGen assessments

- `assessment_sets` — canonical linked assessment JSON
- `flashcards`, `quizzes`, `scenarios` — denormalized promoted items

### Seeded stages

Stage versions use **major.minor** format only (`1.0`, `2.0` — never `1.0.0`).

To repair a wiped or stale `stages` table on an existing project, re-run `supabase/setup/03-seed-stages.sql` (idempotent upsert). See `restore-stages.sql` for the short operator note.

| Module | Stage ID | Version |
|--------|----------|---------|
| intellex | `parse` | 1.0 |
| intellex | `normalize-document` | 1.0 |
| intellex | `trim-document-boundaries` | 1.0 |
| intellex | `structure-document` | 1.0, 1.1, **1.2** (pipeline) |
| intellex | `validate-structure` | 1.0 |
| intellex | `source-research` | 1.0, 2.0, **2.1** (pipeline) |
| intellex | `web-enrichment` | **1.0** (pipeline) |
| intellex | `prepare-document` | 1.0, 2.0 (deactivated) |
| intellex | `deconstruct-document` | 1.0, 2.0 (deactivated) |
| intellex | `extract-knowledge` | 1.0, 2.1 (deactivated — wiki is curated) |
| mathesys | `create-ebook` | 1.0 |
| mathesys | `export-wiki-json` | 1.0 |
| mathesys | `generate-narration` | 1.0 |
| mathesys | `elevenreader-ebook` | 1.0, 2.0 (deactivated) |
| mathesys | `speechify-audio` | 1.0 (deactivated) |
| mathesys | `elevenlabs-audio` | 1.0 (deactivated) |
| qngen | `generate-flashcards` | 1.0, **2.1** |
| qngen | `generate-questions` | 1.0, **2.1** |
| qngen | `generate-scenarios` | 1.0, **2.1** |

The active ingest pipeline uses structuring stages + `source-research` 2.1 + `web-enrichment` 1.0. Older stage versions are kept for foreign-key compatibility with historical `stage_runs`.

**Note:** `source-research` 2.1 and `web-enrichment` 1.0 are required by the current API pipeline. They are seeded here for greenfield installs; existing projects may still need those two rows inserted manually (or via this seed file).

## Fresh vs existing

| Path | Use when |
|------|----------|
| `01`–`04` above | New project, greenfield install |
| `alter-*.sql` / `restore-stages.sql` | Existing project that needs a targeted patch |
