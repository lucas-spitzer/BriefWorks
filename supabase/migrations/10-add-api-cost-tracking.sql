-- Track per-provider API usage and USD cost on skill runs, rolled up to production runs.

alter table public.skill_runs
  add column if not exists api_usage jsonb not null default '{}',
  add column if not exists cost_usd numeric(12, 6) not null default 0;

alter table public.production_runs
  add column if not exists cost_usd numeric(12, 6) not null default 0;

create index if not exists skill_runs_cost_usd_idx on public.skill_runs (cost_usd);
create index if not exists production_runs_cost_usd_idx on public.production_runs (cost_usd);
