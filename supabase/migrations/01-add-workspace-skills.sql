-- Foundation schema: workspaces, skills, sources, production_runs, skill_runs, storage bucket

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- Workspaces
-- ---------------------------------------------------------------------------

create table public.workspaces (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  description text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint workspaces_status_check
    check (status in ('active', 'archived'))
);

create index workspaces_owner_id_idx on public.workspaces (owner_id);

create trigger workspaces_set_updated_at
before update on public.workspaces
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Skills (versioned definitions)
-- ---------------------------------------------------------------------------

create table public.skills (
  id uuid primary key default gen_random_uuid(),
  skill_id text not null,
  version text not null,
  module text not null,
  name text not null,
  description text,
  modalities text[] not null default '{}',
  input_schema jsonb not null default '{}',
  output_schema jsonb not null default '{}',
  prompts jsonb not null default '{}',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  constraint skills_module_check
    check (module in ('intellex', 'mathesys', 'qngen')),
  constraint skills_skill_id_version_key
    unique (skill_id, version)
);

create index skills_module_active_idx
on public.skills (module)
where is_active = true;

-- ---------------------------------------------------------------------------
-- Sources (uploaded files)
-- ---------------------------------------------------------------------------

create table public.sources (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  owner_id uuid not null references auth.users (id) on delete cascade,
  filename text not null,
  mime_type text not null,
  storage_path text not null,
  file_hash text not null,
  file_size_bytes bigint not null,
  source_metadata jsonb not null default '{}',
  status text not null default 'stored',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint sources_status_check
    check (status in ('stored', 'processing', 'ready', 'failed')),
  constraint sources_workspace_file_hash_key
    unique (workspace_id, file_hash)
);

create index sources_workspace_id_idx on public.sources (workspace_id);
create index sources_owner_id_idx on public.sources (owner_id);

create trigger sources_set_updated_at
before update on public.sources
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Production runs (pipeline orchestration)
-- ---------------------------------------------------------------------------

create table public.production_runs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  owner_id uuid not null references auth.users (id) on delete cascade,
  source_ids uuid[] not null default '{}',
  target_artifacts text[] not null default '{}',
  pipeline jsonb not null default '[]',
  status text not null default 'queued',
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint production_runs_status_check
    check (status in ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

create index production_runs_workspace_id_idx on public.production_runs (workspace_id);
create index production_runs_status_idx on public.production_runs (status);

create trigger production_runs_set_updated_at
before update on public.production_runs
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Skill runs (execution + immutable output)
-- ---------------------------------------------------------------------------

create table public.skill_runs (
  id uuid primary key default gen_random_uuid(),
  production_run_id uuid references public.production_runs (id) on delete set null,
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  skill_id text not null,
  skill_version text not null,
  module text not null,
  status text not null default 'queued',
  inputs jsonb not null default '{}',
  output jsonb,
  promoted jsonb not null default '{}',
  model text,
  token_usage jsonb not null default '{}',
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  constraint skill_runs_module_check
    check (module in ('intellex', 'mathesys', 'qngen')),
  constraint skill_runs_status_check
    check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
  constraint skill_runs_skill_fk
    foreign key (skill_id, skill_version)
    references public.skills (skill_id, version)
);

create index skill_runs_production_run_id_idx on public.skill_runs (production_run_id);
create index skill_runs_workspace_id_idx on public.skill_runs (workspace_id);
create index skill_runs_status_idx on public.skill_runs (status);

-- ---------------------------------------------------------------------------
-- Seed v1 skills
-- ---------------------------------------------------------------------------

insert into public.skills (
  skill_id,
  version,
  module,
  name,
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
)
values
  (
    'source-research',
    '1.0.0',
    'intellex',
    'Source Research',
    'Extract and corroborate document metadata from parsed text with web gap-fill.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"parsed_text":{"type":"string"}}}'::jsonb,
    '{"type":"object","required":["document_type","title"],"properties":{"document_type":{"type":"string"},"title":{"type":"string"},"identifier":{"type":"string"},"issuing_authority":{"type":"string"},"authors":{"type":"array"},"version":{"type":"string"},"publication_date_in_document":{"type":"string"},"publication_date_public":{"type":"string"},"source_url":{"type":"string"},"confidence":{"type":"object"},"provenance":{"type":"object"}}}'::jsonb,
    '{"system":"Extract document metadata from parsed text first, then corroborate gaps using public web sources when needed.","user_template":"Source metadata extraction for {{source_id}}."}'::jsonb
  ),
  (
    'deconstruct-document',
    '1.0.0',
    'intellex',
    'Deconstruct Document',
    'Identify essential terms and concepts required to understand a document.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"ndr_segment_ids":{"type":"array"}}}'::jsonb,
    '{"type":"object","required":["concepts"],"properties":{"concepts":{"type":"array"}}}'::jsonb,
    '{"system":"Deconstruct the document into essential terms and concepts. Do not summarize or produce lesson narrative.","user_template":"Extract concepts for source {{source_id}}."}'::jsonb
  ),
  (
    'elevenreader-ebook',
    '1.0.0',
    'mathesys',
    'ElevenReader EBook',
    'Generate a Wiki-aware, content-only EPUB EBook for easy import into ElevenReader.',
    array['text'],
    '{"type":"object","properties":{"source_id":{"type":"string"},"wiki_entry_ids":{"type":"array"}}}'::jsonb,
    '{"type":"object","properties":{"manifest":{"type":"object"},"files":{"type":"array"}}}'::jsonb,
    '{"system":"Transform source text into clean, listenable EPUB prose using canonical wiki terminology.","user_template":"Generate ElevenReader EPUB for source {{source_id}}."}'::jsonb
  );

-- ---------------------------------------------------------------------------
-- Storage bucket for workspace source files
-- ---------------------------------------------------------------------------

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('sources', 'sources', false, null, null)
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- Row level security
-- ---------------------------------------------------------------------------

alter table public.workspaces enable row level security;
alter table public.skills enable row level security;
alter table public.sources enable row level security;
alter table public.production_runs enable row level security;
alter table public.skill_runs enable row level security;

revoke all on table public.workspaces from anon, authenticated;
revoke all on table public.skills from anon, authenticated;
revoke all on table public.sources from anon, authenticated;
revoke all on table public.production_runs from anon, authenticated;
revoke all on table public.skill_runs from anon, authenticated;

-- FastAPI uses the service role key for data access in V1.
