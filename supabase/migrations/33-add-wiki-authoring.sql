-- Wiki authoring: manual knowledge curation replaces automated extraction.
-- (see docs/internal/plans/wiki-authoring-plan.md and wiki-authoring-contract.md)
--
-- 1. wiki_ingest_batches — one row per uploaded notes dump. Draft entries live
--    here as jsonb (contract §3), never as provisional wiki_entries rows, so
--    the wiki table stays 100% canonical and a discarded batch leaves no residue.
-- 2. 'wiki_json' artifact type — the curated wiki is a first-class Mathesys
--    artifact, exportable as a JSON snapshot per source.
-- 3. export-wiki-json stage registration (stage_runs FK requires it).

create table public.wiki_ingest_batches (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  title text not null,
  raw_notes text not null,
  chapter_hint text,
  chapter jsonb,
  status text not null default 'draft',
  entries jsonb not null default '[]',
  unparsed_fragments jsonb not null default '[]',
  model text,
  cost_usd numeric(12, 6),
  committed_entry_ids uuid[] not null default '{}',
  committed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint wiki_ingest_batches_status_check
    check (status in ('draft', 'committed', 'discarded'))
);

create index wiki_ingest_batches_workspace_id_idx
  on public.wiki_ingest_batches (workspace_id);
create index wiki_ingest_batches_source_id_idx
  on public.wiki_ingest_batches (source_id);
create index wiki_ingest_batches_status_idx
  on public.wiki_ingest_batches (workspace_id, status);

create trigger wiki_ingest_batches_set_updated_at
before update on public.wiki_ingest_batches
for each row
execute function public.set_updated_at();

alter table public.wiki_ingest_batches enable row level security;

revoke all on table public.wiki_ingest_batches from anon, authenticated;

-- ---------------------------------------------------------------------------
-- Curated wiki as an exportable Mathesys artifact
-- ---------------------------------------------------------------------------

alter table public.artifacts
  drop constraint if exists artifacts_type_check;

alter table public.artifacts
  add constraint artifacts_type_check
    check (
      artifact_type in (
        'eleven_reader_script',
        'speechify_script',
        'speechify_audio',
        'elevenlabs_audio',
        'wiki_json'
      )
    );

insert into public.stages (
  stage_id,
  version,
  module,
  name,
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
)
values (
  'export-wiki-json',
  '1.0',
  'mathesys',
  'Export Wiki JSON',
  'Snapshot the curated canonical wiki entries for a source into a JSON artifact.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"entry_count":{"type":"integer"}}}'::jsonb,
  '{
    "type": "object",
    "required": ["files", "entry_count"],
    "properties": {
      "files": {"type": "array"},
      "entry_count": {"type": "integer"},
      "entry_kind_counts": {"type": "object"}
    }
  }'::jsonb,
  '{}'::jsonb
)
on conflict (stage_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts;
