-- Existing-database patch: study sheet artifacts and standalone generate jobs.
-- Fresh installs from 01–04 already include this shape. Safe to re-run.

alter table public.artifacts drop constraint if exists artifacts_type_check;

alter table public.artifacts
  add constraint artifacts_type_check
  check (
    artifact_type in (
      'electronic_book',
      'narration_audio',
      'wiki_json',
      'study_sheet'
    )
  );

create table if not exists public.study_sheet_jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  status text not null default 'queued',
  input_filename text not null,
  input_mime_type text not null,
  input_storage_path text not null,
  input_file_size_bytes bigint not null default 0,
  artifact_id uuid references public.artifacts (id) on delete set null,
  attempt_count integer not null default 0,
  page_count integer,
  error text,
  model text,
  cost_usd numeric(12, 6),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint study_sheet_jobs_status_check
    check (status in ('queued', 'running', 'completed', 'failed'))
);

create index if not exists study_sheet_jobs_workspace_id_idx
on public.study_sheet_jobs (workspace_id);
create index if not exists study_sheet_jobs_status_idx
on public.study_sheet_jobs (workspace_id, status);

drop trigger if exists study_sheet_jobs_set_updated_at on public.study_sheet_jobs;
create trigger study_sheet_jobs_set_updated_at
before update on public.study_sheet_jobs
for each row
execute function public.set_updated_at();

alter table public.study_sheet_jobs enable row level security;
revoke all on table public.study_sheet_jobs from anon, authenticated;
