-- Existing-database patch: frozen library slugs and study-sheet source_id.
-- Fresh installs from 01–04 already include this shape.

alter table public.workspaces add column if not exists slug text;

update public.workspaces
set slug = lower(regexp_replace(trim(name), '[^a-zA-Z0-9]+', '-', 'g'))
where slug is null or slug = '';

update public.workspaces
set slug = 'workspace'
where slug is null or slug = '';

alter table public.workspaces alter column slug set not null;

create unique index if not exists workspaces_slug_key on public.workspaces (slug);
create unique index if not exists workspaces_name_lower_key on public.workspaces (lower(name));

alter table public.sources add column if not exists slug text;

update public.sources
set slug = lower(
  regexp_replace(regexp_replace(filename, '\.[^.]+$', ''), '[^a-zA-Z0-9]+', '-', 'g')
)
where slug is null or slug = '';

update public.sources
set slug = 'source'
where slug is null or slug = '';

alter table public.sources alter column slug set not null;

create unique index if not exists sources_workspace_slug_key
on public.sources (workspace_id, slug);

alter table public.study_sheet_jobs
  add column if not exists source_id uuid references public.sources (id) on delete set null;

create index if not exists study_sheet_jobs_source_id_idx
on public.study_sheet_jobs (source_id);

update storage.buckets
set allowed_mime_types = array[
  'application/pdf',
  'text/markdown',
  'application/epub+zip',
  'application/json',
  'audio/mpeg'
]
where id = 'sources';
