-- Assessment Sets: canonical JSON + denormalized item linkage

create table public.assessment_sets (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  skill_run_id uuid references public.skill_runs (id) on delete set null,
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

alter table public.flashcards
  add column assessment_set_id uuid references public.assessment_sets (id) on delete set null,
  add column item_id uuid,
  add column subtype text not null default 'basic';

create index flashcards_assessment_set_id_idx on public.flashcards (assessment_set_id);

alter table public.quizzes
  add column assessment_set_id uuid references public.assessment_sets (id) on delete set null,
  add column item_id uuid,
  add column subtype text;

alter table public.quizzes drop constraint quizzes_question_type_check;

alter table public.quizzes
  add constraint quizzes_question_type_check
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
    );

create index quizzes_assessment_set_id_idx on public.quizzes (assessment_set_id);

alter table public.scenarios
  add column assessment_set_id uuid references public.assessment_sets (id) on delete set null,
  add column item_id uuid,
  add column subtype text not null default 'decision_prompt',
  add column rubric jsonb;

create index scenarios_assessment_set_id_idx on public.scenarios (assessment_set_id);

alter table public.assessment_sets enable row level security;

revoke all on table public.assessment_sets from anon, authenticated;
