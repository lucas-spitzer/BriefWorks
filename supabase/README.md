# BriefWorks Supabase Migrations

## Apply Phase A migration

Run the SQL in the Supabase SQL editor, or use the Supabase CLI if linked:

```bash
supabase db push
```

Migration files (apply in order):

```text
supabase/migrations/20260606120000_phase_a_foundation.sql
supabase/migrations/20260607120000_phase_b_ndr_segments.sql
supabase/migrations/20260608120000_phase_c_source_research_prompt.sql
supabase/migrations/20260609120000_phase_d_wiki_entries.sql
supabase/migrations/20260609130000_phase_d_document_deconstructor_prompt.sql
supabase/migrations/20260610120000_phase_e_artifacts.sql
supabase/migrations/20260611120000_phase_f_assessments.sql
```

## What Phase A creates

- `workspaces`
- `skills` (seeded with v1 Intellex/Mathesys skills)
- `sources`
- `production_runs`
- `skill_runs`
- private Storage bucket `sources`

## What Phase B adds

- `ndr_segments` — chunked NDR text segments with page locators

## What Phase C adds

- Updated `source-research` skill prompt/schema metadata
- No new tables (skill output is stored on `skill_runs.output` and promoted to `sources.source_metadata.research`)

## What Phase D adds

- `wiki_entries` — canonical workspace terms/concepts
- `wiki_disputes` — non-blocking conflict log for competing definitions
- `document-deconstructor` skill promotion into Wiki

## What Phase E adds

- `artifacts` — generated EPUB and future Mathesys outputs
- private Storage bucket `artifacts`
- `eleven-reader-script` skill (Mathesys)

## What Phase F adds

- `flashcards`, `quizzes`, `scenarios` — promoted QnGen assessment entities
- seeded QnGen skills: `flashcard-gen`, `quiz-gen`, `scenario-gen`

## Prerequisites

The auth migration from `docs/internal/authentication-plan.md` should already be applied:

- `profiles`
- `approved_users`

The FastAPI backend uses the service role key for data access in V1. Client roles are revoked from the Phase A–F tables.
