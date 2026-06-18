-- Rename skill IDs and display names for clarity

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
    when 'prepare' then 'prepare-document'
    when 'document-deconstructor' then 'deconstruct-document'
    when 'flashcard-gen' then 'generate-flashcards'
    when 'quiz-gen' then 'generate-questions'
    when 'scenario-gen' then 'generate-scenarios'
  end,
  version,
  module,
  case skill_id
    when 'prepare' then 'Prepare Document'
    when 'document-deconstructor' then 'Deconstruct Document'
    when 'flashcard-gen' then 'Generate Flashcards'
    when 'quiz-gen' then 'Generate Questions'
    when 'scenario-gen' then 'Generate Scenarios'
  end,
  description,
  modalities,
  input_schema,
  output_schema,
  prompts
from public.skills
where skill_id in (
  'prepare',
  'document-deconstructor',
  'flashcard-gen',
  'quiz-gen',
  'scenario-gen'
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
  when 'prepare' then 'prepare-document'
  when 'document-deconstructor' then 'deconstruct-document'
  when 'flashcard-gen' then 'generate-flashcards'
  when 'quiz-gen' then 'generate-questions'
  when 'scenario-gen' then 'generate-scenarios'
  else skill_id
end
where skill_id in (
  'prepare',
  'document-deconstructor',
  'flashcard-gen',
  'quiz-gen',
  'scenario-gen'
);

update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    case
      when elem->>'step' = 'prepare' then
        elem
        || jsonb_build_object('step', 'prepare-document', 'skill_id', 'prepare-document')
      when elem->>'step' = 'document-deconstructor' then
        elem
        || jsonb_build_object('step', 'deconstruct-document', 'skill_id', 'deconstruct-document')
      else elem
    end
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where pipeline @> '[{"step": "prepare"}]'::jsonb
   or pipeline @> '[{"step": "document-deconstructor"}]'::jsonb;

delete from public.skills
where skill_id in (
  'prepare',
  'document-deconstructor',
  'flashcard-gen',
  'quiz-gen',
  'scenario-gen'
);
