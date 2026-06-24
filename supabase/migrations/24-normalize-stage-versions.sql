-- Normalize stage versions from X.Y.0 to X.Y (major.minor only).

create or replace function public.normalize_stage_version(version_text text)
returns text
language sql
immutable
as $$
  select case
    when version_text ~ '^\d+\.\d+\.0$'
      then regexp_replace(version_text, '^(\d+\.\d+)\.0$', '\1')
    else version_text
  end;
$$;

alter table public.stage_runs drop constraint if exists stage_runs_stage_fk;

update public.stages
set version = public.normalize_stage_version(version)
where version ~ '^\d+\.\d+\.0$';

update public.stage_runs
set stage_version = public.normalize_stage_version(stage_version)
where stage_version ~ '^\d+\.\d+\.0$';

update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    case
      when elem ? 'stage_version'
        and elem->>'stage_version' ~ '^\d+\.\d+\.0$'
      then jsonb_set(
        elem,
        '{stage_version}',
        to_jsonb(public.normalize_stage_version(elem->>'stage_version'))
      )
      else elem
    end
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where exists (
  select 1
  from jsonb_array_elements(pipeline) as elem
  where elem ? 'stage_version'
    and elem->>'stage_version' ~ '^\d+\.\d+\.0$'
);

update public.wiki_entries
set origin = jsonb_set(
  origin,
  '{stage_version}',
  to_jsonb(public.normalize_stage_version(origin->>'stage_version'))
)
where origin ? 'stage_version'
  and origin->>'stage_version' ~ '^\d+\.\d+\.0$';

update public.assessment_sets
set origin = jsonb_set(
  origin,
  '{stage_version}',
  to_jsonb(public.normalize_stage_version(origin->>'stage_version'))
)
where origin ? 'stage_version'
  and origin->>'stage_version' ~ '^\d+\.\d+\.0$';

update public.flashcards
set origin = jsonb_set(
  origin,
  '{stage_version}',
  to_jsonb(public.normalize_stage_version(origin->>'stage_version'))
)
where origin ? 'stage_version'
  and origin->>'stage_version' ~ '^\d+\.\d+\.0$';

update public.quizzes
set origin = jsonb_set(
  origin,
  '{stage_version}',
  to_jsonb(public.normalize_stage_version(origin->>'stage_version'))
)
where origin ? 'stage_version'
  and origin->>'stage_version' ~ '^\d+\.\d+\.0$';

update public.scenarios
set origin = jsonb_set(
  origin,
  '{stage_version}',
  to_jsonb(public.normalize_stage_version(origin->>'stage_version'))
)
where origin ? 'stage_version'
  and origin->>'stage_version' ~ '^\d+\.\d+\.0$';

alter table public.stage_runs
  add constraint stage_runs_stage_fk
  foreign key (stage_id, stage_version)
  references public.stages (stage_id, version);

drop function public.normalize_stage_version(text);
