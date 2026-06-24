-- Source Research v2: OpenAI-only document profile extraction.

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
  'source-research',
  '2.0',
  'intellex',
  'Source Research',
  'Extract a source profile from early parsed pages: bibliographic metadata plus purpose, target audience, and scope.',
  array['text'],
  '{"type":"object","properties":{"source_id":{"type":"string"},"filename":{"type":"string"},"mime_type":{"type":"string"},"page_count":{"type":"integer"}}}'::jsonb,
  '{
    "type": "object",
    "required": ["document_type", "title"],
    "properties": {
      "document_type": {"type": "string"},
      "title": {"type": "string"},
      "identifier": {"type": "string"},
      "issuing_authority": {"type": "string"},
      "authors": {"type": "array"},
      "version": {"type": "string"},
      "publication_date_in_document": {"type": "string"},
      "publication_date_public": {"type": "string"},
      "source_url": {"type": "string"},
      "abstract": {"type": "string"},
      "distribution_line": {"type": "string"},
      "purpose": {"type": "string"},
      "target_audience": {"type": "string"},
      "scope": {"type": "string"},
      "confidence": {"type": "object"},
      "provenance": {"type": "object"}
    }
  }'::jsonb,
  '{
    "system": "Extract a source profile from labeled early-page sections of a parsed PDF.",
    "user_template": "Source profile extraction for source {{source_id}}."
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
