-- BriefWorks fresh setup: storage buckets and row-level security.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('sources', 'sources', false, null, null),
  ('artifacts', 'artifacts', false, null, null)
on conflict (id) do nothing;

alter table public.workspaces enable row level security;
alter table public.skills enable row level security;
alter table public.sources enable row level security;
alter table public.production_runs enable row level security;
alter table public.skill_runs enable row level security;
alter table public.ndr_segments enable row level security;
alter table public.document_chapters enable row level security;
alter table public.wiki_entries enable row level security;
alter table public.wiki_disputes enable row level security;
alter table public.artifacts enable row level security;
alter table public.assessment_sets enable row level security;
alter table public.flashcards enable row level security;
alter table public.quizzes enable row level security;
alter table public.scenarios enable row level security;

revoke all on table public.workspaces from anon, authenticated;
revoke all on table public.skills from anon, authenticated;
revoke all on table public.sources from anon, authenticated;
revoke all on table public.production_runs from anon, authenticated;
revoke all on table public.skill_runs from anon, authenticated;
revoke all on table public.ndr_segments from anon, authenticated;
revoke all on table public.document_chapters from anon, authenticated;
revoke all on table public.wiki_entries from anon, authenticated;
revoke all on table public.wiki_disputes from anon, authenticated;
revoke all on table public.artifacts from anon, authenticated;
revoke all on table public.assessment_sets from anon, authenticated;
revoke all on table public.flashcards from anon, authenticated;
revoke all on table public.quizzes from anon, authenticated;
revoke all on table public.scenarios from anon, authenticated;

-- FastAPI uses the service role key for data access in V1.
