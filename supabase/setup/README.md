# BriefWorks Supabase Setup

Use these scripts to bootstrap a **fresh** Supabase project. They contain the full current schema and stage seeds — no incremental refactors or renames.

For existing databases that were built from `supabase/migrations/`, keep using those migration files instead.

## Prerequisites

- A Supabase project with **Google OAuth** configured in Auth (required for sign-in).
- The FastAPI backend uses the **service role** key for data access in V1. Client roles are revoked from application tables.

## Apply setup

Run the SQL files **in order** in the Supabase SQL editor (or pipe them through `psql`):

```text
supabase/setup/01-auth-and-extensions.sql
supabase/setup/02-schema.sql
supabase/setup/03-seed-stages.sql
supabase/setup/04-storage-and-rls.sql
```

Example with the Supabase CLI linked to your project:

```bash
for f in supabase/setup/*.sql; do
  supabase db execute --file "$f"
done
```

After running setup, replace the placeholder owner email in `approved_users` with your own Google account address.

## What gets created

### Auth and extensions

- `approved_users` — internal authorization allowlist
- Extensions: `citext`, `pgcrypto`
- Trigger helper: `set_updated_at()`

### Core tables

- `workspaces`, `sources`, `production_runs`, `stage_runs`, `stages`
- API cost tracking columns on `stage_runs` and `production_runs`

### Intellex content

- `ndr_segments` — chunked parsed text with page locators
- `document_chapters` — persisted chapter/section segmentation
- `wiki_entries` — canonical terms, concepts, and insights (`entry_kind`)
- `wiki_disputes` — non-blocking conflict log

### Mathesys outputs

- `artifacts` — generated EPUB, SSML, and audio files
- Storage buckets: `sources`, `artifacts`

### QnGen assessments

- `assessment_sets` — canonical linked assessment JSON
- `flashcards`, `quizzes`, `scenarios` — denormalized promoted items

### Seeded stages

Stage versions use **major.minor** format only (`1.0`, `2.0` — never `1.0.0`).

To repair a wiped or stale `stages` table on an existing project, re-run `supabase/setup/restore-stages.sql` (idempotent upsert).

| Module | Stage ID | Version |
|--------|----------|---------|
| intellex | `parse` | 1.0 |
| intellex | `normalize-document` | 1.0 |
| intellex | `trim-document-boundaries` | 1.0 |
| intellex | `structure-document` | 1.0 |
| intellex | `validate-structure` | 1.0 |
| intellex | `source-research` | 1.0, 2.0 (inactive), **2.1** (active) |
| intellex | `web-enrichment` | 1.0 |
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

## Migrations vs setup

| Path | Use when |
|------|----------|
| `supabase/setup/` | New project, greenfield install |
| `supabase/migrations/` | Existing project history, incremental upgrades |
