-- QnGen assessment entities (flashcards, quizzes, scenarios)

create table public.flashcards (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  skill_run_id uuid references public.skill_runs (id) on delete set null,
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

create table public.quizzes (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  skill_run_id uuid references public.skill_runs (id) on delete set null,
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
    check (question_type in ('multiple_choice', 'true_false', 'short_answer')),
  constraint quizzes_difficulty_check
    check (difficulty in ('easy', 'medium', 'hard'))
);

create index quizzes_workspace_id_idx on public.quizzes (workspace_id);
create index quizzes_source_id_idx on public.quizzes (source_id);

create table public.scenarios (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  source_id uuid references public.sources (id) on delete set null,
  production_run_id uuid references public.production_runs (id) on delete set null,
  skill_run_id uuid references public.skill_runs (id) on delete set null,
  title text not null,
  prompt text not null,
  context text,
  evaluation_criteria jsonb not null default '[]',
  difficulty text not null default 'medium',
  citations jsonb not null default '[]',
  origin jsonb not null default '{}',
  created_at timestamptz not null default now(),
  constraint scenarios_difficulty_check
    check (difficulty in ('easy', 'medium', 'hard'))
);

create index scenarios_workspace_id_idx on public.scenarios (workspace_id);
create index scenarios_source_id_idx on public.scenarios (source_id);

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
    'generate-flashcards',
    '1.0.0',
    'qngen',
    'Generate Flashcards',
    'Generate memorization flashcards grounded in source segments and canonical wiki terminology.',
    array['text'],
    '{"type":"object"}'::jsonb,
    '{
      "type": "object",
      "required": ["flashcards"],
      "properties": {
        "flashcards": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["front", "back", "difficulty"],
            "properties": {
              "front": {"type": "string"},
              "back": {"type": "string"},
              "difficulty": {"type": "string"},
              "tags": {"type": "array"},
              "wiki_ids_cited": {"type": "array"},
              "segment_ids_used": {"type": "array"}
            }
          }
        }
      }
    }'::jsonb,
    '{
      "system": "Generate memorization flashcards from source material. Use canonical wiki terms exactly.",
      "user_template": "Create flashcards for source {{source_id}}."
    }'::jsonb
  ),
  (
    'generate-questions',
    '1.0.0',
    'qngen',
    'Generate Questions',
    'Generate understanding checks grounded in source segments and canonical wiki terminology.',
    array['text'],
    '{"type":"object"}'::jsonb,
    '{
      "type": "object",
      "required": ["questions"],
      "properties": {
        "questions": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["question", "question_type", "correct_answer", "difficulty"],
            "properties": {
              "question": {"type": "string"},
              "question_type": {"type": "string"},
              "options": {"type": "array"},
              "correct_answer": {"type": "string"},
              "explanation": {"type": "string"},
              "difficulty": {"type": "string"},
              "wiki_ids_cited": {"type": "array"},
              "segment_ids_used": {"type": "array"}
            }
          }
        }
      }
    }'::jsonb,
    '{
      "system": "Generate quiz questions that test understanding of source material.",
      "user_template": "Create quiz questions for source {{source_id}}."
    }'::jsonb
  ),
  (
    'generate-scenarios',
    '1.0.0',
    'qngen',
    'Generate Scenarios',
    'Generate application scenarios grounded in source doctrine and canonical wiki terminology.',
    array['text'],
    '{"type":"object"}'::jsonb,
    '{
      "type": "object",
      "required": ["scenarios"],
      "properties": {
        "scenarios": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["title", "prompt", "difficulty"],
            "properties": {
              "title": {"type": "string"},
              "prompt": {"type": "string"},
              "context": {"type": "string"},
              "evaluation_criteria": {"type": "array"},
              "difficulty": {"type": "string"},
              "wiki_ids_cited": {"type": "array"},
              "segment_ids_used": {"type": "array"}
            }
          }
        }
      }
    }'::jsonb,
    '{
      "system": "Generate realistic application scenarios from source material.",
      "user_template": "Create scenarios for source {{source_id}}."
    }'::jsonb
  )
on conflict (skill_id, version) do nothing;

alter table public.flashcards enable row level security;
alter table public.quizzes enable row level security;
alter table public.scenarios enable row level security;

revoke all on table public.flashcards from anon, authenticated;
revoke all on table public.quizzes from anon, authenticated;
revoke all on table public.scenarios from anon, authenticated;
