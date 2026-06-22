# BriefWorks Supabase

Database bootstrap for BriefWorks. Two paths depending on whether you are starting fresh or upgrading an existing project.

| Path | Use when |
|------|----------|
| [`setup/`](setup/README.md) | New Supabase project — greenfield install |
| [`migrations/`](migrations/) | Existing database — incremental upgrade history |

## Prerequisites

- **Google OAuth** configured in Supabase Auth (required for sign-in).
- The FastAPI backend uses the **service role** key for data access in V1. Client roles are revoked from application tables.

After either path, replace the placeholder owner email in `approved_users` with your own Google account address.

---

## New project setup (recommended)

For a fresh Supabase project, run the consolidated scripts in [`setup/`](setup/README.md). They create the full current schema and stage seeds — no incremental refactors or renames.

```text
supabase/setup/01-auth-and-extensions.sql
supabase/setup/02-schema.sql
supabase/setup/03-seed-stages.sql
supabase/setup/04-storage-and-rls.sql
```

Run them in order in the Supabase SQL editor, or with the CLI linked to your project:

```bash
for f in supabase/setup/*.sql; do
  supabase db execute --file "$f"
done
```

See [`setup/README.md`](setup/README.md) for the full inventory of tables, buckets, and seeded stages.

---

## Migrations (existing databases)

If the database was already built from earlier BriefWorks schema files, apply new changes from `migrations/` in numeric order. Do **not** run the setup scripts on a database that already has BriefWorks tables — use migrations instead.

Run the SQL in the Supabase SQL editor, or use the Supabase CLI if linked:

```bash
supabase db push
```

Migration files (apply in order):

```text
supabase/migrations/00-add-users.sql
supabase/migrations/01-add-workspace-skills.sql
supabase/migrations/02-add-ndr-segments.sql
supabase/migrations/03-update-source-research.sql
supabase/migrations/04-add-wiki-entries.sql
supabase/migrations/05-update-document-deconstructor.sql
supabase/migrations/06-add-artifacts.sql
supabase/migrations/07-add-assessments.sql
supabase/migrations/08-add-narration-artifacts.sql
supabase/migrations/09-mathesys-audio-skills.sql
supabase/migrations/10-add-api-cost-tracking.sql
supabase/migrations/12-update-source-research-metadata-slice.sql
supabase/migrations/13-add-prepare-skill.sql
supabase/migrations/14-add-assessment-sets.sql
supabase/migrations/15-rename-skills.sql
supabase/migrations/16-rename-mathesys-skills.sql
supabase/migrations/17-refocus-prepare-deconstruct.sql
supabase/migrations/18-add-extract-chapter-knowledge.sql
supabase/migrations/19-rename-extract-knowledge.sql
supabase/migrations/19-elevenreader-ebook-v2.sql
supabase/migrations/20-rename-skills-to-stages.sql
supabase/migrations/21-add-parse-stage.sql
supabase/migrations/22-add-structuring-stages.sql
supabase/migrations/23-ensure-core-pipeline-stages.sql
```

### Migration reference

These files record how the schema evolved. The final state they produce is equivalent to running `setup/` on an empty database.

| File | Adds or changes |
|------|-----------------|
| `00-add-users.sql` | `approved_users` allowlist |
| `01-add-workspace-skills.sql` | Core tables, initial skill seeds, `sources` bucket |
| `02-add-ndr-segments.sql` | `ndr_segments` |
| `03-update-source-research.sql` | `source-research` skill metadata |
| `04-add-wiki-entries.sql` | `wiki_entries`, `wiki_disputes` |
| `05-update-document-deconstructor.sql` | `deconstruct-document` skill metadata |
| `06-add-artifacts.sql` | `artifacts`, `artifacts` bucket |
| `07-add-assessments.sql` | `flashcards`, `quizzes`, `scenarios`, QnGen skill seeds |
| `08-add-narration-artifacts.sql` | Expanded `artifacts.artifact_type` values |
| `09-mathesys-audio-skills.sql` | `speechify-audio`, `elevenlabs-audio` skill seeds |
| `10-add-api-cost-tracking.sql` | `api_usage`, `cost_usd` on runs |
| `12-update-source-research-metadata-slice.sql` | `source-research` metadata-slice prompts |
| `13-add-prepare-skill.sql` | `prepare-document` v1.0.0 |
| `14-add-assessment-sets.sql` | `assessment_sets`, assessment linkage columns |
| `15-rename-skills.sql` | Skill ID renames (Intellex + QnGen) |
| `16-rename-mathesys-skills.sql` | Mathesys skill ID renames |
| `17-refocus-prepare-deconstruct.sql` | `document_chapters`, prepare/deconstruct v2.0.0 |
| `18-add-extract-chapter-knowledge.sql` | `wiki_entries.entry_kind`, `extract-knowledge` skill |
| `19-rename-extract-knowledge.sql` | Rename to `extract-knowledge` |
| `19-elevenreader-ebook-v2.sql` | `elevenreader-ebook` v2.0.0 |
| `20-rename-skills-to-stages.sql` | Rename `skills`/`skill_runs` to `stages`/`stage_runs` |
| `21-add-parse-stage.sql` | Register `parse` stage and upgrade pipeline parse step |
| `22-add-structuring-stages.sql` | Structuring stages; deactivate replaced stages |
| `23-ensure-core-pipeline-stages.sql` | `source-research`, `extract-knowledge` for sparse DBs |
