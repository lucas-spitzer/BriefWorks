-- Rename Mathesys skill IDs and remove retired assessment-set-gen skill row

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
  case skill_id
    when 'eleven-reader-script' then 'elevenreader-ebook'
    when 'speechify-api-ssml' then 'speechify-audio'
    when 'elevenlabs-structured-text' then 'elevenlabs-audio'
  end,
  version,
  module,
  name,
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
from public.skills
where skill_id in (
  'eleven-reader-script',
  'speechify-api-ssml',
  'elevenlabs-structured-text'
)
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
set skill_id = case skill_id
  when 'eleven-reader-script' then 'elevenreader-ebook'
  when 'speechify-api-ssml' then 'speechify-audio'
  when 'elevenlabs-structured-text' then 'elevenlabs-audio'
  else skill_id
end
where skill_id in (
  'eleven-reader-script',
  'speechify-api-ssml',
  'elevenlabs-structured-text'
);

update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    case
      when elem->>'step' = 'eleven-reader-script' then
        elem
        || jsonb_build_object('step', 'elevenreader-ebook', 'skill_id', 'elevenreader-ebook')
      when elem->>'step' = 'speechify-api-ssml' then
        elem
        || jsonb_build_object('step', 'speechify-audio', 'skill_id', 'speechify-audio')
      when elem->>'step' = 'elevenlabs-structured-text' then
        elem
        || jsonb_build_object('step', 'elevenlabs-audio', 'skill_id', 'elevenlabs-audio')
      else elem
    end
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where pipeline @> '[{"step": "eleven-reader-script"}]'::jsonb
   or pipeline @> '[{"step": "speechify-api-ssml"}]'::jsonb
   or pipeline @> '[{"step": "elevenlabs-structured-text"}]'::jsonb;

delete from public.skills
where skill_id in (
  'eleven-reader-script',
  'speechify-api-ssml',
  'elevenlabs-structured-text'
);

alter table public.skill_runs drop constraint if exists skill_runs_skill_fk;

delete from public.skills
where skill_id = 'assessment-set-gen';

alter table public.skill_runs
  add constraint skill_runs_skill_fk
  foreign key (skill_id, skill_version)
  references public.skills (skill_id, version)
  not valid;
