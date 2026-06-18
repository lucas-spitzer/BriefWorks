# BriefWorks Supabase Setup

Use these scripts to bootstrap a **fresh** Supabase project. They contain the full current schema and skill seeds — no incremental refactors or renames.

For existing databases that were built from `supabase/migrations/`, keep using those migration files instead.

## Prerequisites

- A Supabase project with **Google OAuth** configured in Auth (required for sign-in).
- The FastAPI backend uses the **service role** key for data access in V1. Client roles are revoked from application tables.

## Apply setup

Run the SQL files **in order** in the Supabase SQL editor (or pipe them through `psql`):

```text
supabase/setup/01-auth-and-extensions.sql
supabase/setup/02-schema.sql
supabase/setup/03-seed-skills.sql
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

- `workspaces`, `sources`, `production_runs`, `skill_runs`, `skills`
- API cost tracking columns on `skill_runs` and `production_runs`

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

### Seeded skills

| Module | Skill ID | Version |
|--------|----------|---------|
| intellex | `source-research` | 1.0.0 |
| intellex | `prepare-document` | 1.0.0, 2.0.0 |
| intellex | `deconstruct-document` | 1.0.0, 2.0.0 |
| intellex | `extract-knowledge` | 1.0.0 |
| mathesys | `elevenreader-ebook` | 1.0.0, 2.0.0 |
| mathesys | `speechify-audio` | 1.0.0 |
| mathesys | `elevenlabs-audio` | 1.0.0 |
| qngen | `generate-flashcards` | 1.0.0 |
| qngen | `generate-questions` | 1.0.0 |
| qngen | `generate-scenarios` | 1.0.0 |

The active pipeline uses `prepare-document` 2.0.0, `deconstruct-document` 2.0.0, `extract-knowledge` 1.0.0, and `elevenreader-ebook` 2.0.0. Older skill versions are kept for foreign-key compatibility.

## Migrations vs setup

| Path | Use when |
|------|----------|
| `supabase/setup/` | New project, greenfield install |
| `supabase/migrations/` | Existing project history, incremental upgrades |
