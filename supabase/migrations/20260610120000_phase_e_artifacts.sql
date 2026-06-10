-- Phase E: Generated artifacts (ElevenReader EPUB, etc.)

create table public.artifacts (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  artifact_type text not null,
  format text not null,
  filename text not null,
  storage_path text not null,
  file_size_bytes bigint not null default 0,
  manifest jsonb not null default '{}',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  constraint artifacts_type_check
    check (artifact_type in ('eleven_reader_script'))
);

create index artifacts_workspace_id_idx on public.artifacts (workspace_id);
create index artifacts_source_id_idx on public.artifacts (source_id);
create index artifacts_production_run_id_idx on public.artifacts (production_run_id);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('artifacts', 'artifacts', false, null, null)
on conflict (id) do nothing;

alter table public.artifacts enable row level security;

revoke all on table public.artifacts from anon, authenticated;
