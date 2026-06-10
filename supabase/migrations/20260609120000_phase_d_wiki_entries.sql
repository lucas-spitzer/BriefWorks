-- Phase D: Wiki entries and dispute logging for Document Deconstructor

create table public.wiki_entries (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  preferred_label text not null,
  canonical_slug text not null,
  definition text not null,
  pronunciation text,
  aliases text[] not null default '{}',
  prerequisites uuid[] not null default '{}',
  importance text not null default 'supporting',
  status text not null default 'canonical',
  evidence jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint wiki_entries_importance_check
    check (importance in ('essential', 'supporting', 'contextual')),
  constraint wiki_entries_status_check
    check (status in ('canonical', 'disputed', 'deprecated', 'rejected')),
  constraint wiki_entries_workspace_slug_key
    unique (workspace_id, canonical_slug)
);

create index wiki_entries_workspace_id_idx on public.wiki_entries (workspace_id);
create index wiki_entries_status_idx on public.wiki_entries (workspace_id, status);

create trigger wiki_entries_set_updated_at
before update on public.wiki_entries
for each row
execute function public.set_updated_at();

create table public.wiki_disputes (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  wiki_entry_id uuid references public.wiki_entries (id) on delete set null,
  term_label text not null,
  existing_definition text,
  proposed_definition text not null,
  skill_run_id uuid references public.skill_runs (id) on delete set null,
  source_id uuid references public.sources (id) on delete set null,
  status text not null default 'open',
  created_at timestamptz not null default now(),
  constraint wiki_disputes_status_check
    check (status in ('open', 'resolved'))
);

create index wiki_disputes_workspace_id_idx on public.wiki_disputes (workspace_id);
create index wiki_disputes_wiki_entry_id_idx on public.wiki_disputes (wiki_entry_id);

alter table public.wiki_entries enable row level security;
alter table public.wiki_disputes enable row level security;

revoke all on table public.wiki_entries from anon, authenticated;
revoke all on table public.wiki_disputes from anon, authenticated;
