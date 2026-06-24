-- Per-workspace LLM model/reasoning overrides for pipeline stages.
--
-- Each row repoints one stage action (source_research, prepare, extract_knowledge,
-- qngen_draft, qngen_critique, assessment_set_gen) at a chosen provider/model for a
-- single workspace. Absent a row, the worker falls back to env vars, then the
-- in-code registry default (see app.llm_actions). Reasoning columns are nullable
-- and reserved for the reasoning-controls work; provider/model drive Phase 2.

create table public.workspace_stage_settings (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces (id) on delete cascade,
  stage_action text not null,
  provider text not null,
  model text not null,
  reasoning_effort text,
  reasoning_tokens integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint workspace_stage_settings_provider_check
    check (provider in ('openai', 'anthropic')),
  constraint workspace_stage_settings_reasoning_tokens_check
    check (reasoning_tokens is null or reasoning_tokens > 0),
  constraint workspace_stage_settings_workspace_action_key
    unique (workspace_id, stage_action)
);

create index workspace_stage_settings_workspace_id_idx
  on public.workspace_stage_settings (workspace_id);

create trigger workspace_stage_settings_set_updated_at
before update on public.workspace_stage_settings
for each row
execute function public.set_updated_at();

alter table public.workspace_stage_settings enable row level security;

revoke all on table public.workspace_stage_settings from anon, authenticated;
