-- Extract Knowledge v2: learning objectives per chapter, evidence quotes, objective mapping.

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
  'extract-knowledge',
  '2.0',
  'intellex',
  'Extract Knowledge',
  'Derive Bloom-aligned learning objectives per chapter, then extract terms, concepts, and insights with evidence quotes and objective mapping.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"chapter_count":{"type":"integer"},"segment_count":{"type":"integer"}}}'::jsonb,
  '{
    "type": "object",
    "properties": {
      "chapters": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "chapter_id": {"type": "string"},
            "chapter_title": {"type": "string"},
            "sequence_index": {"type": "integer"},
            "learning_objectives": {"type": "array"},
            "items": {"type": "array"}
          }
        }
      },
      "items": {"type": "array"},
      "learning_objectives": {"type": "array"},
      "item_counts": {"type": "object"}
    }
  }'::jsonb,
  '{
    "system": "Derive learning objectives for each chapter, then extract grounded terms, concepts, and insights with evidence quotes mapped to objectives.",
    "user_template": "Extract knowledge for chapter {{chapter_title}} in source {{source_id}}."
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
