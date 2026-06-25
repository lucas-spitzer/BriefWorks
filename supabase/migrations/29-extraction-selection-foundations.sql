-- Extraction redesign Phase 0: foundations for scored, gated wiki promotion.
-- Additive and backward-compatible: a new `candidate` status plus nullable
-- audit columns. Existing rows and promotion code are unaffected until later
-- phases populate these.

-- Allow promotion to hold low-signal entries as `candidate` instead of forcing
-- everything to `canonical`. QnGen reads only `canonical`, so candidates are
-- naturally excluded from generation.
alter table public.wiki_entries
  drop constraint if exists wiki_entries_status_check;

alter table public.wiki_entries
  add constraint wiki_entries_status_check
  check (status in ('candidate', 'canonical', 'disputed', 'deprecated', 'rejected'));

-- Auditable selection signals. `confidence` is the extractor's self-rated
-- confidence; `selection_score` is the composite score the curation gate uses.
-- Both nullable; populated by later phases.
alter table public.wiki_entries
  add column if not exists confidence double precision;

alter table public.wiki_entries
  add column if not exists selection_score double precision;

-- Find candidates awaiting promotion without scanning the whole table.
create index if not exists wiki_entries_workspace_status_score_idx
  on public.wiki_entries (workspace_id, status, selection_score);
