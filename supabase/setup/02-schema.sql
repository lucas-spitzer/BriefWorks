-- BriefWorks fresh setup: all application tables (final schema).

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
-- Stages (versioned pipeline step definitions)
-- ---------------------------------------------------------------------------

create table public.stages (
  id uuid primary key default gen_random_uuid(),
  stage_id text not null,
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
  constraint stages_module_check
    check (module in ('intellex', 'mathesys', 'qngen')),
  constraint stages_stage_id_version_key
    unique (stage_id, version)
);

create index stages_module_active_idx
on public.stages (module)
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
  cost_usd numeric(12, 6) not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint production_runs_status_check
    check (status in ('queued', 'running', 'completed', 'failed', 'cancelled'))
);

create index production_runs_workspace_id_idx on public.production_runs (workspace_id);
create index production_runs_status_idx on public.production_runs (status);
create index production_runs_cost_usd_idx on public.production_runs (cost_usd);

create trigger production_runs_set_updated_at
before update on public.production_runs
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Stage runs (execution + immutable output)
-- ---------------------------------------------------------------------------

create table public.stage_runs (
  id uuid primary key default gen_random_uuid(),
  production_run_id uuid references public.production_runs (id) on delete set null,
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  stage_id text not null,
  stage_version text not null,
  module text not null,
  status text not null default 'queued',
  inputs jsonb not null default '{}',
  output jsonb,
  promoted jsonb not null default '{}',
  model text,
  token_usage jsonb not null default '{}',
  api_usage jsonb not null default '{}',
  cost_usd numeric(12, 6) not null default 0,
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz,
  constraint stage_runs_module_check
    check (module in ('intellex', 'mathesys', 'qngen')),
  constraint stage_runs_status_check
    check (status in ('queued', 'running', 'completed', 'failed', 'cancelled')),
  constraint stage_runs_stage_fk
    foreign key (stage_id, stage_version)
    references public.stages (stage_id, version)
);

create index stage_runs_production_run_id_idx on public.stage_runs (production_run_id);
create index stage_runs_workspace_id_idx on public.stage_runs (workspace_id);
create index stage_runs_status_idx on public.stage_runs (status);
create index stage_runs_cost_usd_idx on public.stage_runs (cost_usd);

-- ---------------------------------------------------------------------------
-- NDR segments (parsed and chunked source content)
-- ---------------------------------------------------------------------------

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

-- ---------------------------------------------------------------------------
-- Document chapters (persisted chapter/section segmentation)
-- ---------------------------------------------------------------------------

create table public.document_chapters (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references public.sources (id) on delete cascade,
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  sequence_index integer not null,
  title text not null,
  level integer not null default 1,
  segment_ids uuid[] not null,
  sections jsonb not null default '[]',
  created_at timestamptz not null default now(),
  constraint document_chapters_source_sequence_key
    unique (source_id, sequence_index)
);

create index document_chapters_source_id_idx on public.document_chapters (source_id);
create index document_chapters_workspace_id_idx on public.document_chapters (workspace_id);

-- ---------------------------------------------------------------------------
-- Wiki entries and dispute logging
-- ---------------------------------------------------------------------------

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
  entry_kind text not null default 'concept',
  evidence jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint wiki_entries_importance_check
    check (importance in ('essential', 'supporting', 'contextual')),
  constraint wiki_entries_status_check
    check (status in ('canonical', 'disputed', 'deprecated', 'rejected')),
  constraint wiki_entries_entry_kind_check
    check (entry_kind in ('term', 'concept', 'insight')),
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
  stage_run_id uuid references public.stage_runs (id) on delete set null,
  source_id uuid references public.sources (id) on delete set null,
  status text not null default 'open',
  created_at timestamptz not null default now(),
  constraint wiki_disputes_status_check
    check (status in ('open', 'resolved'))
);

create index wiki_disputes_workspace_id_idx on public.wiki_disputes (workspace_id);
create index wiki_disputes_wiki_entry_id_idx on public.wiki_disputes (wiki_entry_id);

-- ---------------------------------------------------------------------------
-- Generated artifacts
-- ---------------------------------------------------------------------------

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
    check (
      artifact_type in (
        'electronic_book',
        'wiki_json'
      )
    )
);

create index artifacts_workspace_id_idx on public.artifacts (workspace_id);
create index artifacts_source_id_idx on public.artifacts (source_id);
create index artifacts_production_run_id_idx on public.artifacts (production_run_id);

-- ---------------------------------------------------------------------------
-- Assessment sets and promoted QnGen entities
-- ---------------------------------------------------------------------------

create table public.assessment_sets (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  stage_run_id uuid references public.stage_runs (id) on delete set null,
  title text not null,
  learning_goal text,
  assessment_types text[] not null default '{}',
  items jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index assessment_sets_workspace_id_idx on public.assessment_sets (workspace_id);
create index assessment_sets_source_id_idx on public.assessment_sets (source_id);
create index assessment_sets_production_run_id_idx on public.assessment_sets (production_run_id);

create table public.flashcards (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  stage_run_id uuid references public.stage_runs (id) on delete set null,
  assessment_set_id uuid references public.assessment_sets (id) on delete set null,
  item_id uuid,
  subtype text not null default 'basic',
  front text not null,
  back text not null,
  difficulty text not null default 'medium',
  tags text[] not null default '{}',
  citations jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  constraint flashcards_difficulty_check
    check (difficulty in ('easy', 'medium', 'hard'))
);

create index flashcards_workspace_id_idx on public.flashcards (workspace_id);
create index flashcards_source_id_idx on public.flashcards (source_id);
create index flashcards_assessment_set_id_idx on public.flashcards (assessment_set_id);

create table public.quizzes (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  stage_run_id uuid references public.stage_runs (id) on delete set null,
  assessment_set_id uuid references public.assessment_sets (id) on delete set null,
  item_id uuid,
  subtype text,
  question text not null,
  question_type text not null default 'multiple_choice',
  options jsonb not null default '[]',
  correct_answer text not null,
  explanation text,
  difficulty text not null default 'medium',
  citations jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  constraint quizzes_question_type_check
    check (
      question_type in (
        'multiple_choice',
        'true_false',
        'short_answer',
        'multiple_select',
        'true_false_correction',
        'matching',
        'ordering',
        'assertion_reason',
        'compare_contrast'
      )
    ),
  constraint quizzes_difficulty_check
    check (difficulty in ('easy', 'medium', 'hard'))
);

create index quizzes_workspace_id_idx on public.quizzes (workspace_id);
create index quizzes_source_id_idx on public.quizzes (source_id);
create index quizzes_assessment_set_id_idx on public.quizzes (assessment_set_id);

create table public.scenarios (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  stage_run_id uuid references public.stage_runs (id) on delete set null,
  assessment_set_id uuid references public.assessment_sets (id) on delete set null,
  item_id uuid,
  subtype text not null default 'decision_prompt',
  title text not null,
  prompt text not null,
  context text,
  evaluation_criteria jsonb not null default '[]',
  rubric jsonb,
  difficulty text not null default 'medium',
  citations jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  constraint scenarios_difficulty_check
    check (difficulty in ('easy', 'medium', 'hard'))
);

create index scenarios_workspace_id_idx on public.scenarios (workspace_id);
create index scenarios_source_id_idx on public.scenarios (source_id);
create index scenarios_assessment_set_id_idx on public.scenarios (assessment_set_id);
