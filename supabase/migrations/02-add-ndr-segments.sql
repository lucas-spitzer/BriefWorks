-- NDR segments for parsed and chunked source content

create table public.ndr_segments (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources (id) on delete cascade,
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  sequence_index integer not null,
  kind text not null,
  text text not null,
  locator jsonb not null default '{}',
  created_at timestamptz not null default now(),
  constraint ndr_segments_kind_check
    check (kind in ('heading', 'paragraph', 'list_item', 'table', 'caption')),
  constraint ndr_segments_source_sequence_key
    unique (source_id, sequence_index)
);

create index ndr_segments_source_id_idx on public.ndr_segments (source_id);
create index ndr_segments_workspace_id_idx on public.ndr_segments (workspace_id);
create index ndr_segments_source_sequence_idx
on public.ndr_segments (source_id, sequence_index);

alter table public.ndr_segments enable row level security;

revoke all on table public.ndr_segments from anon, authenticated;
