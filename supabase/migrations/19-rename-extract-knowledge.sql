-- Rename extract-chapter-knowledge skill ID and display name

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
select
  'extract-knowledge',
  version,
  module,
  'Extract Knowledge',
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
from public.skills
where skill_id = 'extract-chapter-knowledge'
on conflict (skill_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts;

update public.skill_runs
set skill_id = 'extract-knowledge'
where skill_id = 'extract-chapter-knowledge';

update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    case
      when elem->>'step' = 'extract-chapter-knowledge' then
        elem
        || jsonb_build_object('step', 'extract-knowledge', 'skill_id', 'extract-knowledge')
      else elem
    end
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where pipeline @> '[{"step": "extract-chapter-knowledge"}]'::jsonb;

delete from public.skills
where skill_id = 'extract-chapter-knowledge';
