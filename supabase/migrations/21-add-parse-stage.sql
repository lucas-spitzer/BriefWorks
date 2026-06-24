-- Register parse stage and upgrade pending pipeline definitions.

insert into public.stages (
  stage_id,
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
  'parse',
  '1.0',
  'intellex',
  'Parse Document',
  'Parse PDF sources into structured lines via the LlamaParse API.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"filename":{"type":"string"},"mime_type":{"type":"string"},"file_size_bytes":{"type":"integer"}}}'::jsonb,
  '{
    "type": "object",
    "required": ["page_count", "line_count", "parser", "api_response"],
    "properties": {
      "summary": {"type": "string"},
      "page_count": {"type": "integer"},
      "line_count": {"type": "integer"},
      "parser": {"type": "string"},
      "job_id": {"type": "string"},
      "raw_markdown_path": {"type": "string"},
      "api_response": {"type": "object"}
    }
  }'::jsonb,
  '{
    "system": "Parse uploaded PDF sources into page-aware markdown and normalized document lines.",
    "user_template": "Parse source {{source_id}} ({{filename}})."
  }'::jsonb
)
on conflict (stage_id, version) do update
set
  module = excluded.module,
  name = excluded.name,
  description = excluded.description,
  modalities = excluded.modalities,
  input_schema = excluded.input_schema,
  output_schema = excluded.output_schema,
  prompts = excluded.prompts;

update public.production_runs
set pipeline = (
  select coalesce(jsonb_agg(
    case
      when elem->>'step' = 'parse' then
        (elem - 'type')
        || jsonb_build_object(
          'type', 'stage',
          'stage_id', 'parse',
          'stage_version', '1.0'
        )
      else elem
    end
  ), '[]'::jsonb)
  from jsonb_array_elements(pipeline) as elem
)
where pipeline @> '[{"step": "parse"}]'::jsonb
  and (
    pipeline @> '[{"step": "parse", "type": "deterministic"}]'::jsonb
    or not pipeline::text like '%"stage_id": "parse"%'
  );
