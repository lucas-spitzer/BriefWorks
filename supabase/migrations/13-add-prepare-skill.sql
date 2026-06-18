-- Register Prepare Document skill (GPT narration-body extraction)

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
values (
  'prepare-document',
  '1.0.0',
  'intellex',
  'Prepare Document',
  'Strip non-narration content from parsed documents before chunking using GPT-4o-mini.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"line_count":{"type":"integer"},"page_count":{"type":"integer"}}}'::jsonb,
  '{"type":"object","properties":{"excluded_line_ids":{"type":"array"},"excluded_pages":{"type":"array"},"kept_line_count":{"type":"integer"},"excluded_line_count":{"type":"integer"}}}'::jsonb,
  '{"system":"Identify parsed document content that should not be included in audio narration.","user_template":"Prepare source {{source_id}} for narration."}'::jsonb
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
