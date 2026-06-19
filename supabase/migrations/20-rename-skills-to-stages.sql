-- Rename pipeline "skill" nomenclature to "stage" across schema and stored JSON.

-- Drop FK from stage_runs (still named skill_runs) before table/column renames.
alter table public.skill_runs drop constraint if exists skill_runs_skill_fk;

-- Rename registry and execution tables.
alter table public.skills rename to stages;
alter table public.skill_runs rename to stage_runs;

-- Rename columns on stages.
alter table public.stages rename column skill_id to stage_id;

-- Rename columns on stage_runs.
alter table public.stage_runs rename column skill_id to stage_id;
alter table public.stage_runs rename column skill_version to stage_version;

-- Rename FK columns on dependent tables.
alter table public.wiki_disputes rename column skill_run_id to stage_run_id;
alter table public.assessment_sets rename column skill_run_id to stage_run_id;
alter table public.flashcards rename column skill_run_id to stage_run_id;
alter table public.quizzes rename column skill_run_id to stage_run_id;
alter table public.scenarios rename column skill_run_id to stage_run_id;

-- Rename constraints.
alter table public.stages rename constraint skills_module_check to stages_module_check;
alter table public.stages rename constraint skills_skill_id_version_key to stages_stage_id_version_key;
alter table public.stage_runs rename constraint skill_runs_module_check to stage_runs_module_check;
alter table public.stage_runs rename constraint skill_runs_status_check to stage_runs_status_check;

-- Rename indexes.
alter index if exists skills_module_active_idx rename to stages_module_active_idx;
alter index if exists skill_runs_production_run_id_idx rename to stage_runs_production_run_id_idx;
alter index if exists skill_runs_workspace_id_idx rename to stage_runs_workspace_id_idx;
alter index if exists skill_runs_status_idx rename to stage_runs_status_idx;
alter index if exists skill_runs_cost_usd_idx rename to stage_runs_cost_usd_idx;

-- Re-create FK from stage_runs to stages.
alter table public.stage_runs
  add constraint stage_runs_stage_fk
  foreign key (stage_id, stage_version)
  references public.stages (stage_id, version);

-- Migrate production_runs.pipeline JSONB keys.
update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    (
      elem - 'skill_id' - 'skill_version' - 'skill_run_id'
      || case when elem ? 'skill_id'
        then jsonb_build_object('stage_id', elem->'skill_id')
        else '{}'::jsonb
      end
      || case when elem ? 'skill_version'
        then jsonb_build_object('stage_version', elem->'skill_version')
        else '{}'::jsonb
      end
      || case when elem ? 'skill_run_id'
        then jsonb_build_object('stage_run_id', elem->'skill_run_id')
        else '{}'::jsonb
      end
      || case when elem->>'type' = 'skill'
        then jsonb_build_object('type', 'stage')
        else '{}'::jsonb
      end
    )
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where pipeline @> '[{"type": "skill"}]'::jsonb
   or pipeline::text like '%"skill_id"%'
   or pipeline::text like '%"skill_version"%'
   or pipeline::text like '%"skill_run_id"%';
